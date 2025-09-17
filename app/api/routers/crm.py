# app/api/routers/crm.py

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import date

from app.db.session import get_chatbot_db, get_moodle_db
from app.crud import crm_queries
from app.api.deps import get_current_user
from pydantic import BaseModel

router = APIRouter()

class CaseActionCreate(BaseModel):
    action_type: str
    message_id: Optional[int] = None

class ActionNoteCreate(BaseModel):
    note: str

@router.post("/crm/messages")
def get_crm_messages(
    filters: Dict[str, Any] = Body(...),
    db: Session = Depends(get_chatbot_db),
    moodle_db: Session = Depends(get_moodle_db)
):
    """Obtiene los mensajes para el CRM, agrupados por estudiante."""
    return crm_queries.get_grouped_messages(db, filters, moodle_db)

@router.get("/crm/conversation/{student_phone}")
def get_student_conversation(student_phone: str, db: Session = Depends(get_chatbot_db)):
    """Obtiene el historial de conversación para un estudiante específico."""
    return crm_queries.get_conversation(db, student_phone=student_phone)

@router.post("/crm/students/{student_phone}/actions")
def create_student_action(
    student_phone: str,
    action: CaseActionCreate,
    db: Session = Depends(get_chatbot_db),
    current_user: dict = Depends(get_current_user)
):
    """Crea una acción de caso para un estudiante."""
    return crm_queries.create_case_action(
        db=db,
        student_phone=student_phone,
        action_type=action.action_type,
        user_id=current_user["id"],
        message_id=action.message_id
    )

@router.post("/crm/actions/{action_id}/notes")
def create_action_note(
    action_id: int,
    note: ActionNoteCreate,
    db: Session = Depends(get_chatbot_db),
    current_user: dict = Depends(get_current_user)
):
    """Crea una nota para una acción de caso."""
    return crm_queries.create_action_note(
        db=db,
        action_id=action_id,
        note=note.note,
        user_id=current_user["id"]
    )

@router.get("/crm/messages/{message_id}/actions")
def get_message_actions(message_id: int, db: Session = Depends(get_chatbot_db)):
    """Obtiene las acciones de caso para un mensaje específico."""
    return crm_queries.get_case_actions_for_message(db, message_id)

@router.get("/crm/action_counts") # New endpoint
def get_crm_action_counts(db: Session = Depends(get_chatbot_db)):
    """Obtiene el conteo de acciones de caso por tipo."""
    return crm_queries.get_case_action_counts(db)