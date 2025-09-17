
# app/api/routers/messages.py

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import date

from app.db.session import get_chatbot_db
from app.crud import messages_queries

router = APIRouter()

@router.get("/messages/kpis")
def get_message_kpis(db: Session = Depends(get_chatbot_db)):
    """Obtiene los KPIs de mensajes (total, inbound, outbound)."""
    return messages_queries.get_message_kpis(db)

@router.get("/messages/timeline")
def get_message_timeline(db: Session = Depends(get_chatbot_db)):
    """Obtiene los datos para el gráfico de línea de tiempo de mensajes."""
    return messages_queries.get_timeline_data(db)

@router.post("/messages/table")
def get_filtered_messages(
    filters: Dict[str, Any] = Body(...),
    db: Session = Depends(get_chatbot_db)
):
    """Obtiene los datos de la tabla de mensajes con filtros."""
    return messages_queries.get_filtered_messages(db, filters)
