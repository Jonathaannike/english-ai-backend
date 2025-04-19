# crud.py - CORRECTED FINAL VERSION (Ensure create_comprehension_question is deleted)

from sqlalchemy.orm import Session
from typing import Optional, List
import models
import schemas
# Import hash_password specifically if create_user uses it directly
from auth import hash_password # Assuming verify_password not needed directly in crud

# --- User CRUD Functions ---

def get_user_by_email(db: Session, email: str):
    """Retrieves a user from the database by email."""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Creates a new user in the database."""
    hashed_pwd = hash_password(user.password) # Use the imported function
    db_user = models.User(email=user.email, hashed_password=hashed_pwd)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- Question CRUD Functions ---

def create_question(
    db: Session,
    question_text: str,
    options: list[str],
    correct_option: str,
    lesson_id: Optional[int] = None,
    question_type: Optional[str] = None
) -> models.Question:
    """
    Creates and saves a new question to the database, optionally linking
    it to a lesson and specifying its type.
    """
    db_question = models.Question(
        question_text=question_text,
        options=options,
        correct_option=correct_option,
        lesson_id=lesson_id,
        question_type=question_type
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


# --- Lesson CRUD Functions ---

def create_lesson(db: Session, title: str, level: str, topic: str, text_passage: str) -> models.Lesson:
    """Creates a new Lesson record."""
    db_lesson = models.Lesson(
        title=title,
        level=level,
        topic=topic,
        text_passage=text_passage
    )
    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)
    return db_lesson

def get_lesson(db: Session, lesson_id: int) -> models.Lesson | None:
     """Retrieves a single lesson by ID."""
     # Note: Accessing relationships might trigger lazy loading.
     return db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()


# --- Vocabulary Item CRUD Functions ---

def create_vocabulary_item(db: Session, lesson_id: int, word: str, phonetic_guide: str | None) -> models.VocabularyItem:
    """Creates a new VocabularyItem record linked to a lesson."""
    db_item = models.VocabularyItem(
        lesson_id=lesson_id,
        word=word,
        phonetic_guide=phonetic_guide
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# Ensure create_comprehension_question function is DEFINITELY NOT present below this line