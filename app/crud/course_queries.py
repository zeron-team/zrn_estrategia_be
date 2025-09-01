# app/crud/course_queries.py

from sqlalchemy.orm import Session
from sqlalchemy import text


def get_course_rankings(moodle_db: Session) -> dict:
    """
    Calcula el ratio de aprobación de cada curso y devuelve los
    Top 10 con mayor y menor aprobación.
    """
    # Consulta SQL que calcula el ratio de aprobación por curso
    query = text("""
        SELECT
            c.id AS course_id,
            c.fullname AS course_name,
            -- Calculamos el porcentaje de aprobados
            (SUM(CASE WHEN gg.finalgrade >= 6.0 THEN 1 ELSE 0 END) * 100.0 / COUNT(gg.id)) AS approval_rate
        FROM
            mdl_course c
        JOIN
            mdl_grade_items gi ON c.id = gi.courseid
        JOIN
            mdl_grade_grades gg ON gi.id = gg.itemid
        WHERE
            gi.itemtype = 'course' AND gg.finalgrade IS NOT NULL
        GROUP BY
            c.id, c.fullname
        HAVING 
            COUNT(gg.id) > 5 -- Opcional: solo incluir cursos con más de 5 alumnos calificados
    """)

    results = moodle_db.execute(query).mappings().all()

    # Ordenamos los resultados en Python
    sorted_courses = sorted(results, key=lambda x: x['approval_rate'], reverse=True)

    top_10_approved = sorted_courses[:10]
    top_10_disapproved = sorted(results, key=lambda x: x['approval_rate'])[:10]

    return {
        "top_approved": top_10_approved,
        "top_disapproved": top_10_disapproved
    }