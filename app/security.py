# app/security.py

import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.core.config import settings

# Función para verificar la contraseña usando bcrypt directamente
def verify_password(plain_password: str, hashed_password_str: str) -> bool:
    try:
        # bcrypt necesita que las contraseñas estén en bytes
        plain_password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password_str.encode('utf-8')
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except (ValueError, TypeError):
        return False

# Función para crear un token de acceso JWT (esta no cambia)
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt