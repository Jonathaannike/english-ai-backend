from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from .models import User
from .schemas import UserLogin

# Definir la URL de autorización (se puede usar para el OAuth2)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Clave secreta para codificar y decodificar el token
SECRET_KEY = "tu_clave_secreta"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Tiempo de expiración del token (en minutos)

# Función para obtener al usuario actual a partir del token
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decodificamos el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")  # El 'sub' es el email del usuario
        if email is None:
            raise credentials_exception
        # Recuperamos al usuario de la base de datos
        user = User.get_by_email(email)  # Asegúrate de tener un método para obtener el usuario
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception
