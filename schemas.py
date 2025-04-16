# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None # Changed from 'sub' to 'email' for clarity if that's what you store


# --- User Schemas ---
# Base properties shared by other schemas
class UserBase(BaseModel):
    email: EmailStr # Use EmailStr for validation

# Properties required when creating a user (from request body)
class UserCreate(UserBase):
    password: str # Plain password coming in

# Properties to return to client (never include password hash)
class User(UserBase):
    id: int
    # Add other fields here that are safe to return, e.g.:
    # name: Optional[str] = None
    # is_active: bool

    # This tells Pydantic to read data even if it's not a dict,
    # but an ORM model (or other arbitrary object with attributes)
    class Config:
        from_attributes = True # Changed from orm_mode = True in Pydantic v2

# (Optional) Schema for login if not using OAuth2PasswordRequestForm
class UserLogin(BaseModel):
     email: EmailStr
     password: str