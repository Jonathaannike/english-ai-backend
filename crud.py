# crud.py
from sqlalchemy.orm import Session
import models
import schemas
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

# You can add more functions here: get_user(id), get_users(), update_user(), delete_user()