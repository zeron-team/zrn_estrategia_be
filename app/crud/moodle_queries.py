# app/crud/moodle_queries.py

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from datetime import datetime, time

def get_student_by_phone(db: Session, phone_number: str) -> dict | None:
    """
    Busca a un alumno en la tabla 'students' de la DB del chatbot.
    Esta tabla MAPEA un teléfono a un ID de Moodle.
    """
    query = text("SELECT moodle_user_id, full_name FROM students WHERE phone_number = :phone")
    result = db.execute(query, {"phone": phone_number}).first()
    if result:
        # Usamos ._asdict() para convertir el resultado en un diccionario y evitar problemas de atributos
        return result._asdict()
    return None

def get_final_grade(moodle_db: Session, user_id: int) -> float | None:
    """
    Ejecuta una consulta SQL directa a la base de datos de Moodle
    para obtener la calificación final de un usuario en un curso específico.
    """
    course_id = settings.TARGET_COURSE_ID

    query = text("""
        SELECT gg.finalgrade
        FROM mdl_grade_grades AS gg
        JOIN mdl_grade_items AS gi ON gg.itemid = gi.id
        WHERE gg.userid = :user_id
          AND gi.courseid = :course_id
          AND gi.itemtype = 'course';
    """)

    result = moodle_db.execute(query, {"user_id": user_id, "course_id": course_id}).scalar_one_or_none()

    if result is not None:
        return round(float(result), 2)
    return None

def get_phone_by_moodle_id(db: Session, moodle_user_id: int) -> str | None:
    """
    Busca el número de teléfono de un alumno en la DB del chatbot
    usando su ID de Moodle.
    """
    query = text("SELECT phone_number FROM students WHERE moodle_user_id = :moodle_id")
    result = db.execute(query, {"moodle_id": moodle_user_id}).scalar_one_or_none()
    return result


def get_kpi_data(moodle_db: Session, chatbot_db: Session) -> dict:
    """
    Calcula los KPIs. Aprobados/Desaprobados cuenta el total histórico.
    """
    course_id = settings.TARGET_COURSE_ID

    # Consulta a la DB de Moodle - SIN FILTRO DE FECHA
    moodle_query = text("""
        SELECT
            (SELECT COUNT(DISTINCT u.id) FROM mdl_user u) AS total_contacted,
            COUNT(CASE WHEN gg.finalgrade >= 6.0 THEN 1 END) AS approved,
            COUNT(CASE WHEN gg.finalgrade < 6.0 THEN 1 END) AS disapproved
        FROM mdl_grade_grades gg
        JOIN mdl_grade_items gi ON gg.itemid = gi.id
        WHERE gi.itemtype = 'course' 
          AND gg.finalgrade IS NOT NULL
    """)  # <-- Hemos quitado la línea 'AND gg.timemodified...'

    moodle_result = moodle_db.execute(
        moodle_query,
        {"course_id": course_id}
    ).mappings().first()

    # Consulta a la DB del Chatbot (esta no cambia)
    interactions_query = text("SELECT COUNT(id) AS total_interactions FROM messages")
    chatbot_result = chatbot_db.execute(interactions_query).mappings().first()

    # Combinamos los resultados
    data = {
        "total_contacted": moodle_result["total_contacted"] if moodle_result else 0,
        "approved": moodle_result["approved"] if moodle_result else 0,
        "disapproved": moodle_result["disapproved"] if moodle_result else 0,
        "total_interactions": chatbot_result["total_interactions"] if chatbot_result else 0,
    }
    return data