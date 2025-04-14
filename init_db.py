from database import engine
from models import Base

# Esto crea todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)

print("✅ Migración completada: tablas creadas en la base de datos.")
