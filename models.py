# models.py
from sqlalchemy import Column, Integer, String
# from sqlalchemy.orm import relationship # Not needed yet
from database import Base

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