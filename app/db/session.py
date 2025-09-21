# app/db/session.py
from __future__ import annotations

import os
from typing import Generator, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Cargar el .env si existe
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv()
except Exception:
    pass

def _build_mysql_url(user: Optional[str], password: Optional[str],
                     host: Optional[str], port: Optional[str],
                     name: Optional[str]) -> Optional[str]:
    """Construye una URL MySQL a partir de partes. Devuelve None si falta algo clave."""
    if not all([user, password, host, port, name]):
        return None
    return (
        f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{name}"
        f"?charset=utf8mb4"
    )

# URLs directas si ya están definidas
MOODLE_DATABASE_URL = os.getenv("MOODLE_DATABASE_URL")
CHATBOT_DATABASE_URL = os.getenv("CHATBOT_DATABASE_URL")
GENERIC_URL = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")

# Si no hay URL de Moodle, tratar de armarla con MOODLE_DB_*
if not MOODLE_DATABASE_URL:
    MOODLE_DATABASE_URL = _build_mysql_url(
        os.getenv("MOODLE_DB_USER"),
        os.getenv("MOODLE_DB_PASSWORD"),
        os.getenv("MOODLE_DB_HOST"),
        os.getenv("MOODLE_DB_PORT"),
        os.getenv("MOODLE_DB_NAME"),
    )

# Si no hay URL del Chatbot, armarla con DB_* (tu .env la usa para el CRM)
if not CHATBOT_DATABASE_URL:
    CHATBOT_DATABASE_URL = _build_mysql_url(
        os.getenv("DB_USER"),
        os.getenv("DB_PASSWORD"),
        os.getenv("DB_HOST"),
        os.getenv("DB_PORT"),
        os.getenv("DB_NAME"),
    )

# Fallbacks
if not MOODLE_DATABASE_URL:
    if GENERIC_URL:
        MOODLE_DATABASE_URL = GENERIC_URL
    else:
        print("[session] WARNING: MOODLE_DATABASE_URL no definido; usando SQLite './moodle_fallback.db'.")
        MOODLE_DATABASE_URL = "sqlite:///./moodle_fallback.db"

if not CHATBOT_DATABASE_URL:
    if GENERIC_URL:
        CHATBOT_DATABASE_URL = GENERIC_URL
    else:
        print("[session] WARNING: CHATBOT_DATABASE_URL no definido; usando la conexión de Moodle como fallback.")
        CHATBOT_DATABASE_URL = MOODLE_DATABASE_URL

# Engines / Sessions
engine_moodle = create_engine(MOODLE_DATABASE_URL, pool_pre_ping=True, future=True)
engine_chatbot = create_engine(CHATBOT_DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocalMoodle = sessionmaker(bind=engine_moodle, autoflush=False, autocommit=False, future=True)
SessionLocalChatbot = sessionmaker(bind=engine_chatbot, autoflush=False, autocommit=False, future=True)

# Aliases legacy
engine = engine_moodle
SessionLocal = SessionLocalMoodle

def get_db() -> Generator:
    """Sesión de Moodle (por defecto en casi todos los endpoints de Analytics)."""
    db = SessionLocalMoodle()
    try:
        yield db
    finally:
        db.close()

def get_moodle_db() -> Generator:
    db = SessionLocalMoodle()
    try:
        yield db
    finally:
        db.close()

def get_chatbot_db() -> Generator:
    db = SessionLocalChatbot()
    try:
        yield db
    finally:
        db.close()

# Ping de arranque para detectar problemas temprano (no rompe el arranque)
def _startup_ping():
    try:
        with engine_moodle.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"[session] ERROR conectando a DB Moodle: {e}")
    try:
        with engine_chatbot.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"[session] ERROR conectando a DB Chatbot: {e}")

_startup_ping()