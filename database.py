from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de conexión a tu base de datos en Render
DATABASE_URL = "postgresql://english_ai_db_user:DLJ3OkmshpcGg7Jzi4L6TsyrlUf38ejZ@dpg-cvu58qh5pdvs73e4tla0-a.oregon-postgres.render.com:5432/english_ai_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
