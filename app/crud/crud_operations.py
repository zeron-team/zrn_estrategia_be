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
        to_id=message.to_id,
        template_id=message.template_id
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_all_messages(db: Session, limit: int = 100) -> list:
    """Obtiene los últimos 'limit' mensajes de la base de datos del chatbot."""
    # Asegúrate de seleccionar todas las columnas que necesita el schema MessageInDB
    query = text("""
        SELECT id, sender_id, message_body, direction, timestamp, template_id 
        FROM messages 
        ORDER BY timestamp DESC 
        LIMIT :limit
    """)
    results = db.execute(query, {"limit": limit}).mappings().all()
    return list(results)

def get_last_outgoing_message(db: Session, to_id: str) -> Message | None:
    return db.query(Message).filter(Message.to_id == to_id, Message.direction == 'outgoing').order_by(Message.timestamp.desc()).first()

from app.models.message import DashboardAlert # Import the new model
from app.schemas.alert import DashboardAlertCreate # Need to create this schema

def create_dashboard_alert(db: Session, alert: DashboardAlertCreate) -> DashboardAlert:
    db_alert = DashboardAlert(
        student_phone=alert.student_phone,
        message_id=alert.message_id,
        alert_type=alert.alert_type,
        description=alert.description,
        is_resolved=alert.is_resolved
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert
