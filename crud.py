from sqlalchemy.orm import Session
import models
import schemas


# Create a new user
def create_user(db: Session, email: str, hashed_password: str):
    db_user = models.User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# You can add more CRUD operations here if needed
