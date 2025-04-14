from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from .models import User
from .database import SessionLocal
from .schemas import UserCreate  # Dependiendo de tu esquema de usuario

# 🔑 Clave secreta y algoritmo (usado para crear y decodificar el token)
SECRET_KEY = "mi_clave_super_secreta"
ALGORITHM = "HS256"

# OAuth2PasswordBearer es el mecanismo de FastAPI para recibir el token desde los headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Función para obtener el usuario actual desde el token
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decodifica el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")  # El "sub" es el email que guardamos al generar el token
        if email is None:
            raise credentials_exception
        db = SessionLocal()  # Obtener la sesión de DB
        user = db.query(User).filter(User.email == email).first()  # Buscar al usuario por email
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception
