# app/api/deps.py

from app.services.interfaces import IMoodleService, IWhatsAppService
from app.services.moodle_service import MoodleService
from app.services.whatsapp_service import WhatsAppService # (Debes crear este archivo similar a MoodleService)
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.db.session import get_chatbot_db
from app.crud.auth_queries import get_user
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Principio de Inversión de Dependencias (D):
# FastAPI inyectará una instancia de MoodleService donde se requiera IMoodleService.
# Si mañana creamos un MockMoodleService para tests, solo cambiamos esta línea.
def get_moodle_service() -> IMoodleService:
    return MoodleService()

def get_whatsapp_service() -> IWhatsAppService:
    # Asumimos que WhatsAppService está implementado
    return WhatsAppService()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_chatbot_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user