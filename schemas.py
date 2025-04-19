# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List # Import List

# --- Token Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    # Optional: Schema for data stored inside the JWT token
    email: Optional[EmailStr] = None

# --- User Schemas ---

class UserBase(BaseModel):
    email: EmailStr # Use EmailStr for basic email validation

class UserCreate(UserBase):
    # Schema for data needed when *creating* a user
    password: str

class User(UserBase):
    # Schema for data *returned* about a user (never return password hash)
    id: int

    class Config:
        # Allows Pydantic model to be created from ORM objects (SQLAlchemy models)
        from_attributes = True

class UserLogin(BaseModel):
    # Optional: Schema specifically for user login data
     email: EmailStr
     password: str

# --- AI Exercise Schemas ---

class MultipleChoiceQuestion(BaseModel):
    # Structure for a single generated multiple-choice question
    id: int                  
    question_text: str
    options: List[str]      # Use List from typing
    correct_option: str
    lesson_id: Optional[int] = None     # <<< ADDED: Optional lesson ID
    question_type: Optional[str] = None # <<< ADDED: Optional question type

    class Config:            
        from_attributes = True

class ExerciseResponse(BaseModel):
    # Structure for the overall response from the AI generation endpoint
    exercises: List[MultipleChoiceQuestion] # Use List from typing

class ExerciseGenerationRequest(BaseModel):
    # Structure for the request body when asking for exercises
    topic: str
    level: str
    exercise_type: str
    num_questions: int = 3 # Default to 3 questions if not specified in request

class AnswerSubmission(BaseModel):
    # Represents a single answer sent by the user
    question_id: int       # Which question is being answered
    selected_option: str   # Which option the user chose

class QuizSubmission(BaseModel):
    # Represents the list of answers submitted for a quiz/set of exercises
    answers: List[AnswerSubmission]

class QuizResult(BaseModel):
    # Represents the results returned after submitting answers
    score: int             # Number of correct answers
    total_questions: int   # Total number of questions answered
    # You could add more detail later, like a list of correct/incorrect IDs

# --- Lesson Schemas ---

class LessonGenerationRequest(BaseModel):
    # Schema for the request body when asking to generate a lesson
    topic: str  # e.g., "Daily Routines"
    level: str  # e.g., "B1"

class VocabularyItemResponse(BaseModel):
    # How a single vocabulary item will look in the response
    id: int
    word: str
    phonetic_guide: Optional[str] # Allow for null if AI couldn't generate one
    translation: Optional[str] = None
    

    class Config:
        from_attributes = True # Enable creating from ORM model

class LessonResponse(BaseModel):
    id: int
    title: str
    level: str
    topic: str
    text_passage: str
    vocabulary_items: List[VocabularyItemResponse]
    questions: List[MultipleChoiceQuestion] # <<< MODIFIED: Renamed from comprehension_questions and uses updated MCQ schema

    class Config:
        from_attributes = True

class RichTranslationResponse(BaseModel):
    primary_translation: str
    part_of_speech: Optional[str] = None
    other_meanings: Optional[List[str]] = None # List of alternative translations/meanings
    # We could add example sentences later too