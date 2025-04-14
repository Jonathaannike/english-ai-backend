from pydantic import BaseModel

# Esquema para los datos de creación de un usuario
class UserCreate(BaseModel):
    email: str
    password: str  # La contraseña del usuario

# Esquema para el token de acceso (ya tienes este)
class Token(BaseModel):
    access_token: str
    token_type: str
