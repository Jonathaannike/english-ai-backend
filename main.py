# main.py - CORRECTED FINAL VERSION

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from pydantic import ValidationError

# Import project modules
import crud
import models
import schemas
import auth
from database import get_db # Removed 'engine' as it wasn't used directly here

# Load environment variables from .env file for local development
load_dotenv()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="English Learning App API",
    description="API for user authentication, lesson generation, and quiz submission.",
    version="0.1.0"
)

# --- Configure Gemini API Client (runs once on startup) ---
try:
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        print("Warning: GOOGLE_API_KEY environment variable not set. AI features will be unavailable.")
    else:
        genai.configure(api_key=gemini_api_key)
        print("Gemini API Key configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

# --- Add CORS Middleware ---
# IMPORTANT: Restrict origins in production!
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500", # For VS Code Live Server testing
    # Add your frontend Render URL here later
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication Endpoints ---

@app.post("/register/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new user. Checks if email already exists. Hashes password."""
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    created_user = crud.create_user(db=db, user=user)
    return created_user

@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticates user via OAuth2 Password Flow. Returns JWT access token."""
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- User Endpoints ---

@app.get("/users/me/", response_model=schemas.User, tags=["Users"])
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Returns details of the currently authenticated user. Requires valid JWT."""
    return current_user

# --- Lesson Endpoints ---

@app.post("/lessons", response_model=schemas.LessonResponse, status_code=status.HTTP_201_CREATED, tags=["Lessons"])
async def create_ai_lesson(
    request_data: schemas.LessonGenerationRequest, # Expects topic and level in body
    db: Session = Depends(get_db)
):
    """
    Generates a new lesson unit using AI based on topic and level,
    saves it to the database, and returns the complete lesson data.
    """
    # Build the detailed prompt for the AI
    prompt = f"""Generate content for a mini English lesson unit suitable for a {request_data.level} level learner on the topic "{request_data.topic}".

The output MUST be a single JSON object containing the following keys: "title", "level", "topic", "text_passage", "vocabulary_items", and "comprehension_questions".

1.  **title**: Create a short, engaging title for this lesson unit related to the topic "{request_data.topic}".
2.  **level**: Set this value exactly to "{request_data.level}".
3.  **topic**: Set this value exactly to "{request_data.topic}".
4.  **text_passage**: Generate a short text passage (approximately 80-120 words) describing the topic "{request_data.topic}" using vocabulary and grammar appropriate for a {request_data.level} level. Include relevant concepts or scenarios.
5.  **vocabulary_items**: Extract exactly 10 key vocabulary words or short phrases from the generated `text_passage` that are relevant to the topic and level. For each item in this list, provide a JSON object with the following keys:
    * `word`: The vocabulary word or phrase as a string.
    * `phonetic_guide`: A string representing an *approximate phonetic guide* showing how a typical Colombian Spanish speaker might pronounce the English word if reading it using Spanish phonetic rules or syllables (e.g., for 'usually', guide might be 'yu-shu-a-li'; for 'work', guide might be 'uork'). Be creative but aim for phonetic similarity based on Spanish sounds.
6.  **comprehension_questions**: Generate exactly 3 multiple-choice comprehension questions based *only* on the content of the generated `text_passage`. The questions should check understanding of the main ideas or specific details in the passage. For each question in this list, provide a JSON object with the following keys:
    * `question_text`: A string containing the question.
    * `options`: A list of four strings representing the answer choices. One must be correct based on the passage.
    * `correct_option`: A string containing the correct answer choice from the options list.

Ensure the entire output is valid JSON, starting with {{ and ending with }}. Do not include markdown formatting like ```json before or after the JSON object.
"""
    try:
        # --- Call AI API ---
        print(f"Generating lesson content for topic '{request_data.topic}' ({request_data.level})...")
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

            # --- Save to Database ---
            # 1. Create Lesson
            db_lesson = crud.create_lesson(
                db=db, title=ai_generated_data["title"], level=ai_generated_data["level"],
                topic=ai_generated_data["topic"], text_passage=ai_generated_data["text_passage"]
            )
            print(f"Saved Lesson with ID: {db_lesson.id}")

            # 2. Create Vocabulary Items
            saved_vocab_count = 0
            if isinstance(ai_generated_data.get("vocabulary_items"), list):
                for item_data in ai_generated_data["vocabulary_items"]:
                     if isinstance(item_data, dict) and "word" in item_data:
                        try:
                            crud.create_vocabulary_item(
                                db=db, lesson_id=db_lesson.id, word=item_data["word"],
                                phonetic_guide=item_data.get("phonetic_guide")
                            )
                            saved_vocab_count += 1
                        except Exception as e_voc: print(f"Error saving vocab item {item_data.get('word')}: {e_voc}")
                     else: print(f"Warning: Skipping invalid vocab data from AI: {item_data}")
            print(f"Saved {saved_vocab_count} vocabulary items.")

            # 3. Create Comprehension Questions (using the unified Question model/CRUD)
            saved_question_count = 0
            if isinstance(ai_generated_data.get("comprehension_questions"), list):
                for q_data in ai_generated_data["comprehension_questions"]:
                    if isinstance(q_data, dict) and all(k in q_data for k in ("question_text", "options", "correct_option")):
                        if not isinstance(q_data.get("options"), list): # Ensure options is a list
                            print(f"Warning: Skipping comprehension question with invalid 'options': {q_data}")
                            continue
                        try:
                            # *** THE KEY CHANGE IS HERE: Use crud.create_question ***
                            crud.create_question(
                                db=db,
                                lesson_id=db_lesson.id, # Link to the lesson
                                question_type="comprehension_mcq", # Assign a type
                                question_text=q_data["question_text"],
                                options=q_data["options"],
                                correct_option=q_data["correct_option"]
                            )
                            saved_question_count += 1
                        except Exception as e_q: print(f"Error saving comprehension question {q_data.get('question_text')}: {e_q}")
                    else: print(f"Warning: Skipping invalid comprehension question data from AI: {q_data}")
            print(f"Saved {saved_question_count} comprehension questions.")

            # --- Return the Saved Lesson ---
            # Fetch again to ensure relationships are populated for the response model
            final_lesson_data = crud.get_lesson(db=db, lesson_id=db_lesson.id)
            if not final_lesson_data:
                 raise HTTPException(status_code=404, detail="Failed to retrieve saved lesson data.")

            return final_lesson_data # FastAPI uses schemas.LessonResponse here

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
    """
    Retrieves a specific lesson by its ID, including its vocabulary
    items and comprehension questions (which are just Questions linked to the lesson).
    """
    db_lesson = crud.get_lesson(db, lesson_id=lesson_id)
    if db_lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return db_lesson

# --- Quiz Submission Endpoint ---

@app.post("/submit-answers", response_model=schemas.QuizResult, tags=["Quiz"])
async def submit_answers(
    submission: schemas.QuizSubmission,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Accepts a list of user answers for ANY questions (grammar or comprehension),
    checks them, saves the attempt, and returns the score. Requires authentication.
    """
    correct_count = 0
    total_submitted = len(submission.answers)

    if total_submitted == 0:
        return schemas.QuizResult(score=0, total_questions=0)

    processed_questions = 0 # Count questions we actually find and process
    for answer in submission.answers:
        question = crud.get_question(db=db, question_id=answer.question_id)
        if not question:
            print(f"Warning: Question ID {answer.question_id} not found during submission. Skipping answer.")
            continue # Skip if question doesn't exist

        processed_questions += 1
        is_correct = (answer.selected_option == question.correct_option)
        if is_correct:
            correct_count += 1

        try:
            crud.create_user_answer(
                db=db, user_id=current_user.id, question_id=answer.question_id,
                selected_option=answer.selected_option, is_correct=is_correct
            )
        except Exception as e:
            print(f"Error saving user answer for question {answer.question_id}: {e}")
            # Decide whether to stop or continue despite save error

    # Return score based on questions found and processed
    return schemas.QuizResult(score=correct_count, total_questions=processed_questions)

# --- General Endpoints ---

@app.get("/", tags=["General"])
def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Welcome to the English Learning App API!"}