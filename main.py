from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import crud, models, schemas, auth, database
from fastapi import APIRouter
from auth import get_current_user  # Importar la función para obtener al usuario autenticado

app = FastAPI()

# Crear usuario
@app.post("/register/")
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    hashed_password = auth.hash_password(user.password)
    db_user = crud.create_user(db=db, email=user.email, hashed_password=hashed_password)
    return {"message": f"User {db_user.email} registered successfully!"}

# Login - Generar token
@app.post("/token")
def login_for_access_token(form_data: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == form_data.email).first()
    if not db_user or not auth.pwd_context.verify(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = auth.create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Crear rutas protegidas
@app.get("/me")
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {"email": current_user.email, "name": current_user.name}

# Aquí puedes agregar más rutas protegidas si lo deseas

