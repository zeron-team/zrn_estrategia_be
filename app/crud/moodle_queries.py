# app/crud/moodle_queries.py

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from datetime import datetime, time

def get_students_by_phone_numbers(moodle_db: Session, phone_numbers: list[str]) -> dict[str, str]:
    """
    Obtiene los nombres completos de los estudiantes de Moodle dado una lista de números de teléfono,
    intentando coincidir con diferentes formatos de número.
    Retorna un diccionario mapeando número de teléfono a nombre completo.
    """
    if not phone_numbers:
        return {}

    conditions = []
    params = {}
    phone_map = {}

    for i, phone in enumerate(phone_numbers):
        # phone is like 'whatsapp:+54911...`
        cleaned_phone = phone.replace('whatsapp:+', '') # '54911...'
        phone_map[cleaned_phone] = phone

        param_name = f"phone_{i}"
        params[param_name] = cleaned_phone

        conditions.append(f"phone1 = :{param_name}")
        conditions.append(f"phone1 = CONCAT('+', :{param_name})")
        conditions.append(f"RIGHT(phone1, 9) = RIGHT(:{param_name}, 9)")

    full_condition = " OR ".join(conditions)

    query = text(f"""
        SELECT
            phone1,
            firstname,
            lastname
        FROM mdl_user
        WHERE {full_condition}
    """)

    results = moodle_db.execute(query, params).mappings().all()

    students_data = {}
    for row in results:
        full_name = f"{row['firstname']} {row['lastname']}".strip()
        # Find the original phone number from the map
        original_phone = phone_map.get(row['phone1'])
        if original_phone:
            students_data[original_phone] = full_name
        else:
            # Fallback for partial match
            for cleaned, original in phone_map.items():
                if cleaned.endswith(row['phone1'][-9:]):
                    students_data[original] = full_name
                    break

    return students_data

def get_student_by_phone(moodle_db: Session, phone_number: str) -> dict | None:
    """
    Obtiene el ID de Moodle y el nombre completo de un estudiante
    dado su número de teléfono.
    """
    if not phone_number:
        return None

    cleaned_phone = phone_number.replace('whatsapp:+', '')

    query = text("""
        SELECT
            id AS moodle_user_id,
            firstname,
            lastname
        FROM mdl_user
        WHERE phone1 = :cleaned_phone
           OR phone1 = CONCAT('+', :cleaned_phone)
           OR RIGHT(phone1, 9) = RIGHT(:cleaned_phone, 9)
    """)

    result = moodle_db.execute(query, {"cleaned_phone": cleaned_phone}).mappings().first()

    if result:
        return {
            "moodle_user_id": result["moodle_user_id"],
            "full_name": f"{result['firstname']} {result['lastname']}".strip()
        }
    return None


def get_student_final_grade_by_phone(moodle_db: Session, phone_number: str) -> float | None:
    """
    Obtiene la calificación final de un estudiante dado su número de teléfono.
    """
    student_data = get_student_by_phone(moodle_db, phone_number)
    if student_data:
        return get_final_grade(moodle_db, student_data["moodle_user_id"])
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

def get_course_name_by_id(moodle_db: Session, course_id: int) -> str | None:
    """
    Obtiene el nombre de un curso dado su ID.
    """
    query = text("SELECT fullname FROM mdl_course WHERE id = :course_id")
    result = moodle_db.execute(query, {"course_id": course_id}).scalar_one_or_none()
    return result

def get_student_course_exam_history(moodle_db: Session, user_id: int) -> dict:
    """
    Obtiene el historial de exámenes (calificaciones) de un estudiante por curso.
    """
    query = text("""
        SELECT
            c.fullname AS course_name,
            gi.itemname AS exam_name,
            gg.finalgrade,
            gg.timemodified
        FROM mdl_grade_grades AS gg
        JOIN mdl_grade_items AS gi ON gg.itemid = gi.id
        JOIN mdl_course AS c ON gi.courseid = c.id
        WHERE gg.userid = :user_id
          AND gi.itemtype = 'mod_quiz' -- Assuming exams are quizzes
          AND gg.finalgrade IS NOT NULL
        ORDER BY c.fullname, gg.timemodified ASC;
    """)

    results = moodle_db.execute(query, {"user_id": user_id}).mappings().all()

    course_exam_history = {}
    for row in results:
        course_name = row['course_name']
        if course_name not in course_exam_history:
            course_exam_history[course_name] = []
        
        # Determine status based on finalgrade (assuming 6.0 is passing)
        status = "gray" # Default
        if row['finalgrade'] >= 6.0:
            status = "green"
        elif row['finalgrade'] < 6.0 and row['finalgrade'] is not None:
            status = "red"
        elif row['finalgrade'] == 0: # Assuming 0 means absent or not taken
            status = "orange"

        course_exam_history[course_name].append({
            "exam_name": row['exam_name'],
            "status": status,
            "timestamp": row['timemodified']
        })
    
    return course_exam_history

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

def get_course_id_by_name(moodle_db: Session, course_name: str) -> int | None:
    """
    Obtiene el ID de un curso dado su nombre completo.
    """
    query = text("SELECT id FROM mdl_course WHERE fullname = :course_name")
    result = moodle_db.execute(query, {"course_name": course_name}).scalar_one_or_none()
    return result




