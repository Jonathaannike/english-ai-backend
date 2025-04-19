# models.py - CORRECTED FINAL VERSION

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# Use the import that worked for init_db.py previously
from database import Base
# If the above causes import errors later, you might revert to:
# from .database import Base # (Only if running as part of a formal package)

# --- User Model ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
    # Relationship to UserAnswer defined below


# --- Lesson Models ---
class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    level = Column(String, index=True)
    topic = Column(String, index=True)
    text_passage = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships defined here
    vocabulary_items = relationship("VocabularyItem", back_populates="lesson", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="lesson", cascade="all, delete-orphan")


# models.py - MODIFY the VocabularyItem class

class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    word = Column(String, nullable=False)
    phonetic_guide = Column(String, nullable=True)
    translation = Column(String, nullable=True) 

    lesson = relationship("Lesson", back_populates="vocabulary_items")


# --- Unified Question Model ---
class Question(Base): # The single, correct, updated Question model
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String, nullable=False)
    options = Column(JSON, nullable=False) # Expects list of strings ideally
    correct_option = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Link to Lesson (nullable because not all questions might belong to a lesson)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True, index=True)
    # Type of question (e.g., 'grammar_mcq', 'comprehension_mcq', 'vocab_mcq')
    question_type = Column(String, index=True, nullable=True)

    # Relationships defined here
    lesson = relationship("Lesson", back_populates="questions")
    user_answers = relationship("UserAnswer", back_populates="question", cascade="all, delete-orphan")


# --- User Answer Model ---
class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False) # Links to the unified Question model
    selected_option = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships defined here
    # Added cascade option to User relationship if needed
    user = relationship("User") # Can add back_populates="answers" to User if a user needs easy access to all their answers
    question = relationship("Question", back_populates="user_answers")

# Ensure the old/duplicate Question class is NOT present anywhere else in this file.
# Ensure the ComprehensionQuestion class is NOT present anywhere else in this file.