# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import os # To load secret key from environment
from dotenv import load_dotenv # To load .env file for local dev

import models
import schemas
from database import SessionLocal, get_db # Import get_db if you need a session here

load_dotenv() # Load .env file variables

# --- Configuration ---
# !! IMPORTANT: Store SECRET_KEY in environment variable !!
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None:
    # Fallback only for local testing *if* you don't use .env, but raise error is better
    # SECRET_KEY = "a_very_bad_default_secret_key_replace_me"
    raise ValueError("SECRET_KEY environment variable not set.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Or get from environment variable

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- Token Creation ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- OAuth2 Scheme ---
# tokenUrl should match the path operation where tokens are created (your login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# --- Dependency to get current user ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Decodes JWT token to get the current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Assuming you store the user's email in the 'sub' (subject) claim
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        # Optional: Validate token data structure using Pydantic schema
        # token_data = schemas.TokenData(email=email)
    except JWTError:
        # Catches errors like expired signature, invalid signature etc.
        raise credentials_exception

    # Get user from database
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        # This case means the user existed when token was issued, but not anymore
        raise credentials_exception

    # Optional: Check if user is active
    # if not user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")

    return user # Return the database model instance