# app/db/session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# --- Conexión a la Base de Datos del Chatbot ---
CHATBOT_DB_URL = f"mysql+mysqlconnector://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Añadimos pool_recycle y pool_pre_ping para mantener la conexión viva
engine_chatbot = create_engine(
    CHATBOT_DB_URL,
    pool_recycle=3600,  # Recicla la conexión cada hora
    pool_pre_ping=True  # Verifica la conexión antes de cada uso
)
SessionLocalChatbot = sessionmaker(autocommit=False, autoflush=False, bind=engine_chatbot)


# --- Conexión a la Base de Datos de Moodle (Solo Lectura) ---
MOODLE_DB_URL = f"mysql+mysqlconnector://{settings.MOODLE_DB_USER}:{settings.MOODLE_DB_PASSWORD}@{settings.MOODLE_DB_HOST}:{settings.MOODLE_DB_PORT}/{settings.MOODLE_DB_NAME}"

# Hacemos lo mismo para la conexión de Moodle
engine_moodle = create_engine(
    MOODLE_DB_URL,
    pool_recycle=3600,
    pool_pre_ping=True
)
SessionLocalMoodle = sessionmaker(autocommit=False, autoflush=False, bind=engine_moodle)


# --- Dependencias de FastAPI para inyectar las sesiones ---
def get_chatbot_db():
    db = SessionLocalChatbot()
    try:
        yield db
    finally:
        db.close()

def get_moodle_db():
    db = SessionLocalMoodle()
    try:
        yield db
    finally:
        db.close()