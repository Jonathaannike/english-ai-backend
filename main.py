# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # Use standard form for login
from sqlalchemy.orm import Session
from typing import List # To potentially return lists later

import crud
import models
import schemas
import auth
from database import engine, get_db # Import get_db and potentially engine/Base if needed directly

# Create tables if they don't exist (Simple approach for development)
# For production, use Alembic for migrations
# models.Base.metadata.create_all(bind=engine) # Moved this logic to init_db.py

app = FastAPI(
    title="English Learning App API",
    description="API for user authentication and potentially other features.",
    version="0.1.0"
)

# === User Registration ===
@app.post("/register/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user.
    Checks if email already exists.
    Hashes the password before saving.
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    created_user = crud.create_user(db=db, user=user)
    return created_user


# === Login - Generate Token ===
@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates user with email (as username) and password.
    Returns JWT access token upon success. Uses OAuth2 Password Flow.
    """
    user = crud.get_user_by_email(db, email=form_data.username) # Use email from form's username field

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(
        data={"sub": user.email} # 'sub' (subject) is standard claim for user identifier
    )
    return {"access_token": access_token, "token_type": "bearer"}


# === Protected Route Example: Get Current User ===
@app.get("/users/me/", response_model=schemas.User, tags=["Users"])
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """
    Returns the details of the currently authenticated user.
    Requires authentication (valid JWT token).
    """
    # current_user is the ORM model instance from the database
    # FastAPI automatically converts it to the schemas.User response model
    return current_user


# === Root Endpoint ===
@app.get("/", tags=["General"])
def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Welcome to the English Learning App API!"}


# === Additional User Endpoints (Example) ===
# @app.get("/users/{user_id}", response_model=schemas.User, tags=["Users"])
# def read_user(user_id: int, db: Session = Depends(get_db)):
#     db_user = db.query(models.User).filter(models.User.id == user_id).first()
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user