from sqlalchemy.orm import Session
from models import User
from schemas import UserCreate

# Create a new user
def create_user(db: Session, email: str, hashed_password: str):
    db_user = User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# You can add more CRUD operations here if needed
