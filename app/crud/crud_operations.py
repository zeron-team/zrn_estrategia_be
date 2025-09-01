# app/crud/crud_operations.py

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.message import Message
from app.schemas.message import MessageCreate

def create_message(db: Session, message: MessageCreate) -> Message:
    db_message = Message(
        sender_id=message.sender_id,
        message_body=message.message_body,
        direction=message.direction,
        to_id=message.to_id  # <-- AÑADE ESTA LÍNEA
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_all_messages(db: Session, limit: int = 100) -> list:
    """Obtiene los últimos 'limit' mensajes de la base de datos del chatbot."""
    # Asegúrate de seleccionar todas las columnas que necesita el schema MessageInDB
    query = text("""
        SELECT id, sender_id, message_body, direction, timestamp 
        FROM messages 
        ORDER BY timestamp DESC 
        LIMIT :limit
    """)
    results = db.execute(query, {"limit": limit}).mappings().all()
    return list(results)