from pydantic import BaseModel

# User registration schema (used for POST request body)
class UserCreate(BaseModel):
    email: str
    password: str

    class Config:
        orm_mode = True
