# app/api/routers/interactions.py

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import date

from app.db.session import get_chatbot_db
from app.crud import interactions_queries # Crearemos este archivo ahora

router = APIRouter()

@router.get("/interactions/kpis")
def get_interaction_kpis(db: Session = Depends(get_chatbot_db)):
    """Obtiene los KPIs de interacciones (total, inbound, outbound)."""
    return interactions_queries.get_interaction_kpis(db)

@router.get("/interactions/timeline")
def get_interaction_timeline(db: Session = Depends(get_chatbot_db)):
    """Obtiene los datos para el gráfico de línea de tiempo."""
    return interactions_queries.get_timeline_data(db)

@router.post("/interactions/table")
def get_filtered_interactions(
    filters: Dict[str, Any] = Body(...),
    db: Session = Depends(get_chatbot_db)
):
    """Obtiene los datos de la tabla de interacciones con filtros."""
    return interactions_queries.get_filtered_messages(db, filters)