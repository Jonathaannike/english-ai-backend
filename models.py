from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON # Added Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # To set default timestamps
from database import Base # Assuming Base is defined in database.py in the same directory

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # Add other fields here if needed later, e.g.:
    # name = Column(String, index=True)
    # is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
    
# models.py
# ... (keep existing User class) ...

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String, nullable=False)
    # Store options as JSON list ["option A", "option B", ...]
    options = Column(JSON, nullable=False)
    correct_option = Column(String, nullable=False)
    # Optional: Add level, topic etc. if you want to categorize stored questions
    # level = Column(String, index=True)
    # topic = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to user answers (one question can have many answers)
    user_answers = relationship("UserAnswer", back_populates="question")


class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Link to User table
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False) # Link to Question table
    selected_option = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    # Optional: Add attempt_id if grouping answers into quizzes/attempts
    # attempt_id = Column(Integer, ForeignKey("attempts.id"))
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships to access User and Question objects from an answer
    user = relationship("User") # No back_populates needed if User model doesn't link back
    question = relationship("Question", back_populates="user_answers")