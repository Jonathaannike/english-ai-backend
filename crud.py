# crud.py
from sqlalchemy.orm import Session
import models
import schemas
from auth import hash_password
# No need to import auth here usually, keep concerns separate

def get_user_by_email(db: Session, email: str):
    """Retrieves a user from the database by email."""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Creates a new user in the database."""
    # Import hash_password here or pass the hashed password directly
    from auth import hash_password
    hashed_password = hash_password(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Question CRUD Functions ---

def create_question(db: Session, question_text: str, options: list[str], correct_option: str) -> models.Question:
    """Creates and saves a new question to the database."""
    db_question = models.Question(
        question_text=question_text,
        options=options, # SQLAlchemy handles JSON conversion for JSON type
        correct_option=correct_option
        # Add level/topic here if you added them to the model
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

def get_question(db: Session, question_id: int) -> models.Question | None:
    """Retrieves a question from the database by its ID."""
    return db.query(models.Question).filter(models.Question.id == question_id).first()

# --- User Answer CRUD Functions ---

def create_user_answer(db: Session, user_id: int, question_id: int, selected_option: str, is_correct: bool) -> models.UserAnswer:
    """Creates and saves a user's answer to the database."""
    db_user_answer = models.UserAnswer(
        user_id=user_id,
        question_id=question_id,
        selected_option=selected_option,
        is_correct=is_correct
    )
    db.add(db_user_answer)
    db.commit()
    db.refresh(db_user_answer)
    return db_user_answer