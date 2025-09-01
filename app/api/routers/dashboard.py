# app/api/routers/dashboard.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_chatbot_db, get_moodle_db
from app.crud import crud_operations, moodle_queries
from app.schemas.kpi import KpiData
from app.schemas.message import MessageInDB # Asumiendo que MessageInDB está bien definido

router = APIRouter()

@router.get("/kpis", response_model=KpiData)
def read_kpis(
    moodle_db: Session = Depends(get_moodle_db),
    chatbot_db: Session = Depends(get_chatbot_db) # <-- Añadimos la segunda DB
):
    """Endpoint para obtener los KPIs."""
    # Pasamos ambas sesiones a la función
    kpi_data = moodle_queries.get_kpi_data(moodle_db=moodle_db, chatbot_db=chatbot_db)
    return kpi_data


@router.get("/messages", response_model=List[MessageInDB])
def read_messages(chatbot_db: Session = Depends(get_chatbot_db)):
    """Endpoint para obtener el historial de mensajes."""
    messages = crud_operations.get_all_messages(chatbot_db, limit=100)
    return messages