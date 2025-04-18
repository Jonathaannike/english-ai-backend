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

@app.post("/generate/exercise", response_model=schemas.ExerciseResponse, tags=["AI Generation"])
async def generate_exercise(params: schemas.ExerciseGenerationRequest): # Correct signature
    """
    Generates exercises based on input parameters (topic, level, type, quantity).
    Output is validated against the ExerciseResponse schema.
    """
    # --- Build the prompt dynamically using input parameters ---
    # This logic now belongs INSIDE the function
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
    # This entire try/except block also belongs INSIDE the function
    try:
        print(f"Generating {params.num_questions} {params.exercise_type} questions for {params.level} on '{params.topic}'...") # Updated log
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Use the dynamically generated 'prompt' variable
        response = await model.generate_content_async(prompt)
        print("Received response from Gemini API (/generate/exercise).") # Updated log

        # --- Process and Validate the Response ---
        try:
            response_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            generated_exercises_raw = json.loads(response_text)
            validated_response = schemas.ExerciseResponse(exercises=generated_exercises_raw)
            return validated_response

        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from AI response: {response.text}")
            raise HTTPException(status_code=500, detail="AI returned non-JSON formatted content.")
        except ValidationError as e:
            print(f"Error: AI response failed validation: {e}. Response: {response.text}")
            raise HTTPException(status_code=500, detail="AI response format did not match expected structure.")
        except Exception as e_proc:
             print(f"Error processing AI response: {type(e_proc).__name__} - {e_proc}")
             raise HTTPException(status_code=500, detail="Error processing AI response.")

    except Exception as e_api:
        print(f"Error during Gemini API call (/generate/exercise): {type(e_api).__name__} - {e_api}") # Updated log
        raise HTTPException(status_code=500, detail="Failed to generate content due to an API error.")

# --- End of the generate_exercise function ---

# Your other endpoints like @app.get("/", ...) should follow after this function