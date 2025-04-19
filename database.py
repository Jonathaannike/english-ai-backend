# database.py - Updated Version with Explicit Schema & Env Var Handling

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData # <<< Import MetaData
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv() # Load .env file for local runs

# Get DATABASE_URL from environment variable (recommended)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    # If not found in environment, fall back to the hardcoded one you provided
    # (You should ideally have it set in your .env file locally)
    DATABASE_URL = "postgresql://english_ai_db_user:DLJ3OkmshpcGg7Jzi4L6TsyrlUf38ejZ@dpg-cvu58qh5pdvs73e4tla0-a.oregon-postgres.render.com:5432/english_ai_db"
    print("Warning: DATABASE_URL environment variable not found, using hardcoded fallback.")
    # Alternatively, you could raise an error here if the env var is absolutely required:
    # raise ValueError("DATABASE_URL environment variable not set.")

# Define the target schema explicitly (usually 'public' for default PostgreSQL)
SCHEMA_NAME = "public"
# Create a MetaData object with the schema specified
metadata_obj = MetaData(schema=SCHEMA_NAME) # <<< Define MetaData with schema

# Create the engine (no changes here)
engine = create_engine(DATABASE_URL)

# Create the session factory (no changes here)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the Base class using declarative_base, passing our metadata object
Base = declarative_base(metadata=metadata_obj) # <<< Pass metadata here

# Dependency function to get a DB session (no changes here)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Optional: Confirmation message on import/startup
print(f"Database connection configured for schema '{SCHEMA_NAME}'.")