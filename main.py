# main.py - FINAL CORRECTED VERSION (v3 - Correct Vocab Prompt)

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from pydantic import ValidationError # Although not explicitly caught, good practice

# Import project modules
import crud
import models
import schemas
import auth
from database import get_db

# Load environment variables
load_dotenv()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="English Learning App API",
    description="API for user authentication, AI lesson generation/retrieval, AI translation, and quiz submission.",
    version="0.1.0"
)

# --- Configure Gemini API Client ---
try:
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        print("Warning: GOOGLE_API_KEY environment variable not set. AI features might be unavailable.")
    else:
        genai.configure(api_key=gemini_api_key)
        print("Gemini API Key configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

# --- CORS Middleware ---
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500", # For VS Code Live Server testing
    # Add Render frontend URL later
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- Authentication Endpoints ---

@app.post("/register/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new user."""
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    created_user = crud.create_user(db=db, user=user)
    return created_user

@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticates user. Returns JWT."""
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- User Endpoints ---

@app.get("/users/me/", response_model=schemas.User, tags=["Users"])
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Returns details of the currently authenticated user."""
    return current_user

# --- Lesson Endpoints ---

@app.post("/lessons", response_model=schemas.LessonResponse, status_code=status.HTTP_201_CREATED, tags=["Lessons"])
async def create_ai_lesson(
    request_data: schemas.LessonGenerationRequest, db: Session = Depends(get_db)
):
    """Generates, saves, and returns a new lesson unit using AI."""
    topic = request_data.topic
    level = request_data.level
    # Build the detailed prompt for the AI - ensuring vocab asks for all fields
    prompt = f"""Generate content for a mini English lesson unit suitable for a {level} level learner on the topic "{topic}".

The output MUST be a single JSON object containing the following keys: "title", "level", "topic", "text_passage", "vocabulary_items", and "comprehension_questions".

1.  **title**: Create a short, engaging title for this lesson unit related to the topic "{topic}".
2.  **level**: Set this value exactly to "{level}".
3.  **topic**: Set this value exactly to "{topic}".
4.  **text_passage**: Generate a short text passage (approximately 80-120 words) describing the topic "{topic}" using vocabulary and grammar appropriate for a {level} level. Include relevant concepts or scenarios.
5.  **vocabulary_items**: Extract exactly 10 key vocabulary words or short phrases from the generated `text_passage` that are relevant to the topic and level. For each item in this list, provide a JSON object with the following EXACT keys:
    * `word`: The vocabulary word or phrase as a string.
    * `phonetic_guide`: A string representing an *approximate phonetic guide* showing how a typical Colombian Spanish speaker might pronounce the English word if reading it using Spanish phonetic rules or syllables (e.g., 'usually' -> 'yu-shu-a-li'; 'work' -> 'uork').
    * `translation`: A string providing the Spanish translation of the word *as it is most likely used in the context of the generated text passage*. # <<< Ensure this is requested
6.  **comprehension_questions**: Generate exactly 6 multiple-choice comprehension questions based *only* on the content of the generated `text_passage`. The questions should check understanding of the main ideas or specific details in the passage. For each question in this list, provide a JSON object with the following keys:
    * `question_text`: A string containing the question.
    * `options`: A list of four strings representing the answer choices. One must be correct based on the passage.
    * `correct_option`: A string containing the correct answer choice from the options list.

Ensure the entire output is valid JSON, starting with {{ and ending with }}. Do not include markdown formatting like ```json before or after the JSON object.
"""
    try:
        # --- Call AI API ---
        print(f"Generating lesson content for topic '{topic}' ({level})...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        print("Received response from Gemini API.")

        # --- Process, Validate, and Save the Response ---
        try:
            response_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            ai_generated_data = json.loads(response_text)

            required_keys = ["title", "level", "topic", "text_passage", "vocabulary_items", "comprehension_questions"]
            if not isinstance(ai_generated_data, dict) or not all(key in ai_generated_data for key in required_keys):
                raise ValueError("AI response structure is invalid or missing required keys.")

            # Save Lesson
            db_lesson = crud.create_lesson(
                db=db, title=ai_generated_data["title"], level=ai_generated_data.get("level", level), # Use AI level or request level
                topic=ai_generated_data.get("topic", topic), text_passage=ai_generated_data["text_passage"]
            )
            print(f"Saved Lesson with ID: {db_lesson.id}")

            # Save Vocabulary Items
            saved_vocab_count = 0
            if isinstance(ai_generated_data.get("vocabulary_items"), list):
                for item_data in ai_generated_data["vocabulary_items"]:
                     if isinstance(item_data, dict) and "word" in item_data:
                        try:
                            # Pass all fields received from AI (using .get for safety) to CRUD function
                            crud.create_vocabulary_item(
                                db=db, lesson_id=db_lesson.id, word=item_data["word"],
                                phonetic_guide=item_data.get("phonetic_guide"),
                                translation=item_data.get("translation") # Pass translation
                            )
                            saved_vocab_count += 1
                        except Exception as e_voc: print(f"Error saving vocab item {item_data.get('word')}: {e_voc}")
                     else: print(f"Warning: Skipping invalid vocab data from AI: {item_data}")
            print(f"Saved {saved_vocab_count} vocabulary items.")

            # Save Comprehension Questions
            saved_question_count = 0
            if isinstance(ai_generated_data.get("comprehension_questions"), list):
                for q_data in ai_generated_data["comprehension_questions"]:
                    if isinstance(q_data, dict) and all(k in q_data for k in ("question_text", "options", "correct_option")):
                        if not isinstance(q_data.get("options"), list):
                            print(f"Warning: Skipping question with invalid 'options': {q_data}")
                            continue
                        try:
                            crud.create_question(
                                db=db, lesson_id=db_lesson.id, question_type="comprehension_mcq",
                                question_text=q_data["question_text"], options=q_data["options"],
                                correct_option=q_data["correct_option"]
                            )
                            saved_question_count += 1
                        except Exception as e_q: print(f"Error saving question {q_data.get('question_text')}: {e_q}")
                    else: print(f"Warning: Skipping invalid question data from AI: {q_data}")
            print(f"Saved {saved_question_count} comprehension questions.")

            # Return the Saved Lesson
            final_lesson_data = crud.get_lesson(db=db, lesson_id=db_lesson.id)
            if not final_lesson_data:
                 raise HTTPException(status_code=404, detail="Failed to retrieve saved lesson data after creation.")
            return final_lesson_data

        except (json.JSONDecodeError, ValueError) as e_parse:
            print(f"Error parsing/validating AI JSON response: {e_parse}. Response: {response.text}")
            raise HTTPException(status_code=500, detail=f"AI response format error: {e_parse}")
        except Exception as e_proc:
             print(f"Error processing/saving AI response: {type(e_proc).__name__} - {e_proc}")
             raise HTTPException(status_code=500, detail="Error processing or saving AI response.")

    except Exception as e_api:
        print(f"Error during Gemini API call: {type(e_api).__name__} - {e_api}")
        raise HTTPException(status_code=500, detail="Failed to generate lesson content due to an API error.")


@app.get("/lessons/{lesson_id}", response_model=schemas.LessonResponse, tags=["Lessons"])
def read_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """Retrieves a specific lesson by its ID, including its items."""
    db_lesson = crud.get_lesson(db, lesson_id=lesson_id)
    if db_lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return db_lesson

# --- Translation Endpoint (Using Gemini) ---

@app.get("/translate", response_model=schemas.RichTranslationResponse, tags=["Translation"])
async def translate_word_with_ai(word: str, target_language: str = 'es'):
    """Provides richer translation details for a word using Gemini."""
    if not word:
        raise HTTPException(status_code=400, detail="No 'word' provided for translation.")

    prompt = f"""Provide translation details for the English word "{word}" into Spanish ({target_language}). Consider common usages. Return ONLY a single JSON object with keys: "primary_translation" (string), "part_of_speech" (string or null), "other_meanings" (list of strings, max 3). Example for "book": {{"primary_translation": "libro", "part_of_speech": "noun", "other_meanings": ["reservar"]}}. Now provide the JSON for "{word}":"""
    try:
        print(f"Getting rich translation for '{word}' via Gemini...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        print("Received response from Gemini for translation.")
        try:
            response_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            ai_generated_data = json.loads(response_text)
            if not isinstance(ai_generated_data, dict) or "primary_translation" not in ai_generated_data:
                 raise ValueError("AI response is not a valid dictionary or missing 'primary_translation'.")
            return ai_generated_data # Pydantic validates via response_model
        except (json.JSONDecodeError, ValueError) as e_parse:
            print(f"Error parsing/validating AI JSON translation response: {e_parse}. Response: {response.text}")
            raise HTTPException(status_code=500, detail=f"AI translation response format error: {e_parse}")
    except Exception as e_api:
        print(f"Error during Gemini API call for translation: {type(e_api).__name__} - {e_api}")
        raise HTTPException(status_code=500, detail="Failed to get translation due to an API error.")


# --- Quiz Submission Endpoint ---

@app.post("/submit-answers", response_model=schemas.QuizResult, tags=["Quiz"])
async def submit_answers(
    submission: schemas.QuizSubmission, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)
):
    """Accepts answers, checks them, saves attempt, returns score."""
    correct_count = 0
    total_submitted = len(submission.answers)
    if total_submitted == 0: return schemas.QuizResult(score=0, total_questions=0)

    processed_questions = 0
    for answer in submission.answers:
        question = crud.get_question(db=db, question_id=answer.question_id)
        if not question:
            print(f"Warning: Question ID {answer.question_id} not found during submission.")
            continue
        processed_questions += 1
        is_correct = (answer.selected_option == question.correct_option)
        if is_correct: correct_count += 1
        try:
            crud.create_user_answer(
                db=db, user_id=current_user.id, question_id=answer.question_id,
                selected_option=answer.selected_option, is_correct=is_correct
            )
        except Exception as e: print(f"Error saving user answer for question {answer.question_id}: {e}")

    return schemas.QuizResult(score=correct_count, total_questions=processed_questions)

# --- General Endpoints ---

@app.get("/", tags=["General"])
def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Welcome to the English Learning App API!"}

# Removed the global translate_client initialization block and related import