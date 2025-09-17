# app/crud/crm_queries.py

from sqlalchemy.orm import Session
from app.models.message import Message, CaseAction, ActionNote
from sqlalchemy import func, desc, or_, text
from typing import Dict, Any, List, Optional
from app.crud import moodle_queries # Import moodle_queries
import collections
from datetime import datetime
from app.core.config import settings
import re

TEMPLATE_SIDS = {
    "PASSED": "HXd4eaa70446b9fa2998717a0881553efd",
    "FAILED": "HXdf67b79ece430528680858878b6a269a",
    "ABSENT": "HX5841cadee3381b3b5ced40b5a068b5db",
}

def get_grouped_messages(db: Session, filters: Dict[str, Any], moodle_db: Session):
    """
    Obtiene los mensajes agrupados por estudiante (nombre completo) para el CRM.
    Para cada estudiante, devuelve todos los mensajes y las acciones del caso.
    """
    # 1. Obtener todos los mensajes (o un subconjunto filtrado por fecha)
    base_query = db.query(Message)

    if filters.get("start_date"):
        base_query = base_query.filter(Message.timestamp >= filters["start_date"])
    if filters.get("end_date"):
        base_query = base_query.filter(Message.timestamp <= filters["end_date"])

    all_messages = base_query.order_by(Message.timestamp.desc()).all()

    # 2. Agrupar mensajes por número de teléfono del estudiante
    BOT_NUMBER = settings.TWILIO_FROM_NUMBER
    messages_by_student_phone = collections.defaultdict(list)
    student_phones = set()

    for message in all_messages:
        student_phone = None
        if message.sender_id == BOT_NUMBER:
            student_phone = message.to_id
        else:
            student_phone = message.sender_id
        
        if student_phone:
            messages_by_student_phone[student_phone].append(message)
            student_phones.add(student_phone)

    # 3. Obtener nombres de estudiantes de Moodle
    students_names_map = moodle_queries.get_students_by_phone_numbers(moodle_db, list(student_phones))

    # 4. Preparar la lista de estudiantes con todos sus mensajes y aplicar filtros
    student_list = []
    student_name_filter = filters.get("student_name", "").lower()

    for student_phone, messages in messages_by_student_phone.items():
        full_name = students_names_map.get(student_phone, f"UNKNOWN_STUDENT_{student_phone}")

        # Aplicar filtro de nombre de estudiante en Python
        if student_name_filter and student_name_filter not in full_name.lower():
            continue # Skip if name doesn't match filter

        # Sort messages by timestamp ascending for chronological display
        sorted_messages = sorted(messages, key=lambda msg: msg.timestamp)

        # Extract relevant message data
        formatted_messages = []
        for msg in sorted_messages:
            formatted_messages.append({
                "id": msg.id,
                "message_body": msg.message_body,
                "timestamp": msg.timestamp.isoformat(),
                "sender_id": msg.sender_id,
                "to_id": msg.to_id,
                "direction": msg.direction,
                "template_id": msg.template_id
            })

        actions = get_case_actions_for_student(db, student_phone) if student_phone else []

        final_grade = moodle_queries.get_student_final_grade_by_phone(moodle_db, student_phone)
        
        course_message_exam_history = collections.defaultdict(list)
        for msg in formatted_messages:
            course_name = None
            if msg["template_id"] == TEMPLATE_SIDS["PASSED"]:
                # Example: "¡Felicitaciones, Andrea Soledad! 🎉 Vimos que has aprobado tu examen de 1 - ADMINISTRACIÓN ADM. ¡Excelente trabajo! Sigue así, estás cada vez más cerca de tu meta. 💪"
                match = re.search(r"examen de (.*?)\. ¡Excelente trabajo!", msg["message_body"])
                if match:
                    course_name = match.group(1).strip()
            elif msg["template_id"] == TEMPLATE_SIDS["FAILED"]:
                # Example: "Hola Ana Irene Jesus. Vimos tu resultado en el examen de 1 - SISTEMAS OPERATIVOS. No te preocupes, esto es una oportunidad para reforzar los temas. Para poder ayudarte mejor, ¿podrías contarnos cuál fue el principal motivo?"
                match = re.search(r"examen de (.*?)\. No te preocupes", msg["message_body"])
                if match:
                    course_name = match.group(1).strip()
            elif msg["template_id"] == TEMPLATE_SIDS["ABSENT"]:
                # Example: "Hola Fabio Rene, notamos que tienes pendiente el examen de 2025 - RDLS - 3° TECNOLOGÍA E IMPLEMENTACIÓN- HIDRO. Queremos asegurarnos de que todo esté bien."
                match = re.search(r"examen de (.*?)\. Queremos asegurarnos", msg["message_body"])
                if match:
                    course_name = match.group(1).strip()

            if course_name:
                course_message_exam_history[course_name].append({
                    "template_id": msg["template_id"],
                    "timestamp": msg["timestamp"]
                })
        
        print(f"Course Message Exam History for {full_name}: {course_message_exam_history}") # NEW DEBUG LINE

        student_list.append({
            "student_name": full_name,
            "student_phone": student_phone,
            "messages": formatted_messages,
            "case_actions": actions,
            "final_grade": final_grade,
            "course_message_exam_history": course_message_exam_history # NEW
        })
    
    return student_list

def get_conversation(db: Session, student_phone: str):
    """
    Obtiene todos los mensajes de una conversación con un estudiante.
    """
    return db.query(Message).filter(
        or_(Message.sender_id == student_phone, Message.to_id == student_phone)
    ).order_by(Message.timestamp.asc()).all()

def create_case_action(db: Session, student_phone: str, action_type: str, user_id: int, message_id: Optional[int] = None) -> CaseAction:
    """
    Crea una nueva acción de caso para un estudiante, opcionalmente asociada a un mensaje.
    """
    print(f"Received message_id: {message_id}, type: {type(message_id)}")
    db_action = CaseAction(
        student_phone=student_phone,
        message_id=message_id, # New field
        action_type=action_type,
        user_id=user_id,
        timestamp=datetime.utcnow()
    )
    db.add(db_action)
    db.commit()
    db.refresh(db_action)
    return db_action

def create_action_note(db: Session, action_id: int, note: str, user_id: int) -> ActionNote:
    """
    Crea una nueva nota para una acción de caso.
    """
    db_note = ActionNote(
        action_id=action_id,
        note=note,
        user_id=user_id,
        timestamp=datetime.utcnow()
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def get_case_actions_for_student(db: Session, student_phone: str) -> List[Dict[str, Any]]:
    """
    Obtiene todas las acciones de caso para un estudiante, incluyendo el nombre del usuario y las notas.
    """
    actions = db.query(CaseAction).filter(CaseAction.student_phone == student_phone).all()
    
    results = []
    for action in actions:
        user_query = text("SELECT username FROM crm_users WHERE id = :user_id")
        user_result = db.execute(user_query, {"user_id": action.user_id}).first()
        user_name = user_result[0] if user_result else "Unknown"
        
        notes_query = db.query(ActionNote).filter(ActionNote.action_id == action.id).order_by(ActionNote.timestamp.desc()).all()
        notes = []
        for note in notes_query:
            note_user_query = text("SELECT username FROM crm_users WHERE id = :user_id")
            note_user_result = db.execute(note_user_query, {"user_id": note.user_id}).first()
            note_user_name = note_user_result[0] if note_user_result else "Unknown"
            notes.append({
                "note": note.note,
                "user_name": note_user_name,
                "timestamp": note.timestamp
            })

        results.append({
            "id": action.id,
            "action_type": action.action_type,
            "user_name": user_name,
            "timestamp": action.timestamp,
            "notes": notes
        })
    return results

def get_case_actions_for_message(db: Session, message_id: int) -> List[Dict[str, Any]]:
    """
    Obtiene todas las acciones de caso para un mensaje específico, incluyendo el nombre del usuario y las notas.
    """
    actions = db.query(CaseAction).filter(CaseAction.message_id == message_id).all()
    
    results = []
    for action in actions:
        user_query = text("SELECT username FROM crm_users WHERE id = :user_id")
        user_result = db.execute(user_query, {"user_id": action.user_id}).first()
        user_name = user_result[0] if user_result else "Unknown"
        
        notes_query = db.query(ActionNote).filter(ActionNote.action_id == action.id).order_by(ActionNote.timestamp.desc()).all()
        notes = []
        for note in notes_query:
            note_user_query = text("SELECT username FROM crm_users WHERE id = :user_id")
            note_user_result = db.execute(note_user_query, {"user_id": note.user_id}).first()
            note_user_name = note_user_result[0] if note_user_result else "Unknown"
            notes.append({
                "note": note.note,
                "user_name": note_user_name,
                "timestamp": note.timestamp
            })

        results.append({
            "id": action.id,
            "action_type": action.action_type,
            "user_name": user_name,
            "timestamp": action.timestamp,
            "notes": notes
        })
    return results

def get_case_action_counts(db: Session) -> Dict[str, int]:
    """
    Obtiene el conteo de acciones de tipo 'case_taken' y 'manual_contact'.
    """
    query = text("""
        SELECT
            COUNT(CASE WHEN action_type = 'case_taken' THEN 1 END) AS case_taken_count,
            COUNT(CASE WHEN action_type = 'manual_contact' THEN 1 END) AS manual_contact_count
        FROM case_actions
    """)
    result = db.execute(query).mappings().first()
    return dict(result) if result else {"case_taken_count": 0, "manual_contact_count": 0}