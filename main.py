# main.py
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

import crud
import models
import schemas
import auth
from database import engine, get_db


# Load environment variables from .env file for local development
load_dotenv()

app = FastAPI(
    title="English Learning App API",
    description="API for user authentication and potentially other features.",
    version="0.1.0"
)

# Configure Gemini API Client (runs once on startup)
try:
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        print("Warning: GOOGLE_API_KEY environment variable not set. AI features will be unavailable.")
    else:
        genai.configure(api_key=gemini_api_key)
        print("Gemini API Key configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

# Add CORS Middleware
# IMPORTANT: Restrict origins in production! Replace broad list/wildcard.
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500",
    # e.g., "https://your-app-name.onrender.com"
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

# --- AI Generation Endpoints ---

@app.post("/generate-test", tags=["AI Generation"])
async def generate_test_text():
    """A simple test endpoint to generate text using the configured Gemini model."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "Explain what an API is in one simple sentence for a beginner."

        print("Sending request to Gemini API (/generate-test)...")
        response = await model.generate_content_async(prompt)
        print("Received response from Gemini API (/generate-test).")

        if not response.text:
             print(f"Gemini response finished but lacked text. Feedback: {response.prompt_feedback}")
             raise HTTPException(status_code=500, detail="AI model did not return text content.")

        return {"generated_text": response.text}
    except Exception as e:
        print(f"Error during Gemini API call (/generate-test): {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail="Failed to generate content due to an internal error.")

# main.py - Find and update the endpoint definition

# Change the path from "/generate/mcq" to "/generate/exercise"
# Change the function name from "generate_mcq_exercise" to "generate_exercise"
# Add the 'params: schemas.ExerciseGenerationRequest' argument

# Replace the ENTIRE generate_exercise function in main.py with this:

@app.post("/generate/exercise", response_model=schemas.ExerciseResponse, tags=["AI Generation"])
async def generate_exercise(params: schemas.ExerciseGenerationRequest, db: Session = Depends(get_db)):
    """
    Generates exercises based on input parameters (topic, level, type, quantity),
    saves them to the database, and returns the saved exercises with their IDs.
    Output is validated against the ExerciseResponse schema.
    """
    # --- Build the prompt dynamically using input parameters ---
    prompt = f"""Generate exactly {params.num_questions} {params.exercise_type.replace('_', ' ')} grammar questions suitable for a {params.level} level English learner, focusing specifically on the topic: "{params.topic}".

For each question, provide:
1. A sentence relevant to the topic with a blank space to be filled or a verb in parentheses to be conjugated.
2. Four distinct options as potential answers, where only one option is grammatically correct for the tense/topic required by the context. Include the correct answer among the options.
3. The correct option string (exactly as it appears in the options list).

Please format the entire output strictly as a single JSON list. Each element in the list must be a JSON object representing one question, with the following exact keys:
- "question_text": A string containing the question sentence.
- "options": A list of four strings representing the answer choices.
- "correct_option": A string containing the correct answer choice from the options list.

Example for a different topic:
{{
  "question_text": "My keys are ___ the table.",
  "options": ["at", "in", "on", "by"],
  "correct_option": "on"
}}
"""
    # --- End of dynamic prompt building ---

    # --- API Call and Response Processing ---
    try:
        print(f"Generating {params.num_questions} {params.exercise_type} questions for {params.level} on '{params.topic}'...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        print("Received response from Gemini API (/generate/exercise).")

        # --- Process, Validate, and SAVE the Response ---
        try:
            response_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            generated_exercises_raw = json.loads(response_text) # Should be a list of dicts

            if not isinstance(generated_exercises_raw, list):
                print(f"Error: AI response was not a JSON list: {response_text}")
                raise ValueError("AI response was not a JSON list.")

            saved_questions_orm = [] # To store the Question ORM objects AFTER saving
            for exercise_data in generated_exercises_raw:
                # Basic validation of the dict structure from AI before saving
                if not isinstance(exercise_data, dict) or not all(k in exercise_data for k in ("question_text", "options", "correct_option")):
                    print(f"Warning: Skipping invalid exercise data format from AI: {exercise_data}")
                    continue # Skip this malformed item

                # Ensure options is a list (basic type check)
                if not isinstance(exercise_data.get("options"), list):
                     print(f"Warning: Skipping exercise data with invalid 'options' format: {exercise_data}")
                     continue

                try:
                    # Create question in DB using CRUD function
                    saved_q = crud.create_question(
                        db=db,
                        question_text=str(exercise_data["question_text"]),
                        options=list(exercise_data["options"]), # Ensure it's a list
                        correct_option=str(exercise_data["correct_option"])
                        # Optional: Add level=params.level, topic=params.topic if storing them
                    )
                    saved_questions_orm.append(saved_q)
                except Exception as db_error: # Catch potential DB errors during save
                    print(f"Error saving question to DB: {db_error}. Data: {exercise_data}")
                    # Decide if you want to continue saving others or raise immediately
                    # For now, we just log and continue

            # Check if we successfully saved any questions after the loop
            if not saved_questions_orm:
                 print(f"Error: No valid exercises could be saved from AI response: {response.text}")
                 raise HTTPException(status_code=500, detail="Failed to process or save any valid exercises from AI response.")

            # Create the final response using the list of saved ORM objects.
            # Pydantic converts based on schemas.ExerciseResponse & schemas.MultipleChoiceQuestion Config
            final_response = schemas.ExerciseResponse(exercises=saved_questions_orm)
            return final_response

        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from AI response: {response.text}")
            raise HTTPException(status_code=500, detail="AI returned non-JSON formatted content.")
        # Removed explicit ValidationError catch as Pydantic handles conversion at the end
        except ValueError as val_err: # Catch explicit ValueErrors we raised
             print(f"Error validating AI response structure: {val_err}. Response: {response_text}")
             raise HTTPException(status_code=500, detail=f"Invalid data structure from AI: {val_err}")
        except Exception as e_proc:
             print(f"Error processing/saving AI response: {type(e_proc).__name__} - {e_proc}")
             raise HTTPException(status_code=500, detail="Error processing or saving AI response.")

    except Exception as e_api:
        print(f"Error during Gemini API call (/generate/exercise): {type(e_api).__name__} - {e_api}")
        raise HTTPException(status_code=500, detail="Failed to generate content due to an API error.")

# --- End of the generate_exercise function ---

@app.post("/submit-answers", response_model=schemas.QuizResult, tags=["Quiz"])
async def submit_answers(
    submission: schemas.QuizSubmission, # Expects a body matching QuizSubmission schema
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user) # PROTECTED: Requires authentication
):
    """
    Accepts a list of user answers, checks them against the database,
    saves the attempt, and returns the score. Requires authentication.
    """
    correct_count = 0
    total_count = len(submission.answers) # Total questions answered in this submission

    if total_count == 0:
        # Handle empty submission if necessary
        return schemas.QuizResult(score=0, total_questions=0)

    for answer in submission.answers:
        # Get the corresponding question from the DB
        question = crud.get_question(db=db, question_id=answer.question_id)

        if not question:
            # Handle case where question ID submitted doesn't exist
            # Option 1: Skip this answer
            print(f"Warning: Question ID {answer.question_id} not found. Skipping answer.")
            # Option 2: Raise an error (might be better)
            # raise HTTPException(status_code=404, detail=f"Question with ID {answer.question_id} not found.")
            continue # Using Option 1 for now

        # Check if the selected option is correct (case-sensitive comparison for now)
        is_correct = (answer.selected_option == question.correct_option)

        if is_correct:
            correct_count += 1

        # Save the user's answer attempt to the database
        try:
            crud.create_user_answer(
                db=db,
                user_id=current_user.id, # Get ID from logged-in user
                question_id=answer.question_id,
                selected_option=answer.selected_option,
                is_correct=is_correct
            )
        except Exception as e:
            # Log error if saving answer fails, but potentially continue scoring
            print(f"Error saving user answer for question {answer.question_id}: {e}")
            # Depending on requirements, you might want to handle this more robustly

    # Return the results
    return schemas.QuizResult(score=correct_count, total_questions=total_count)