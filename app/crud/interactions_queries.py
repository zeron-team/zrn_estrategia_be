# app/crud/interactions_queries.py

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any


def get_interaction_kpis(db: Session) -> Dict[str, int]:
    """Cuenta el total de interacciones, entrantes y salientes."""
    query = text("""
        SELECT
            COUNT(id) AS total_interactions,
            COUNT(CASE WHEN direction = 'incoming' THEN 1 END) AS inbound_count,
            COUNT(CASE WHEN direction = 'outgoing' THEN 1 END) AS outbound_count
        FROM messages
    """)
    result = db.execute(query).mappings().first()
    return dict(result) if result else {"total_interactions": 0, "inbound_count": 0, "outbound_count": 0}


def get_timeline_data(db: Session) -> list:
    """Agrupa las interacciones por día para el gráfico."""
    query = text("""
        SELECT
            DATE(timestamp) AS date,
            COUNT(id) AS count
        FROM messages
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
        LIMIT 30
    """)  # Limitamos a los últimos 30 días con datos
    results = db.execute(query).mappings().all()
    return [{"date": str(r['date']), "count": r['count']} for r in results]


def get_filtered_messages(db: Session, filters: Dict[str, Any]) -> list:
    """
    Obtiene mensajes y busca el nombre del remitente y del destinatario,
    corrigiendo el filtro por nombre de alumno.
    """
    base_query = """
        SELECT
            m.id,
            m.direction,
            m.message_body,
            m.timestamp,
            m.sender_id,
            m.to_id,
            s_sender.full_name AS sender_name,
            s_receiver.full_name AS receiver_name
        FROM messages m
        LEFT JOIN students s_sender ON m.sender_id = s_sender.phone_number
        LEFT JOIN students s_receiver ON m.to_id = s_receiver.phone_number
        WHERE 1=1
    """
    params = {}

    # Applying filters dynamically...
    if filters.get("student_name"):
        # --- CORRECCIÓN ---
        # El filtro de nombre ahora se aplica a la conversación general
        # Se buscan los IDs de los mensajes que pertenecen a conversaciones
        # con un alumno que coincide con el nombre.
        base_query += """ AND m.id IN (
            SELECT m2.id FROM messages m2
            LEFT JOIN students s2 ON m2.sender_id = s2.phone_number OR m2.to_id = s2.phone_number
            WHERE s2.full_name LIKE :student_name
        )"""
        params["student_name"] = f"%{filters['student_name']}%"

    if filters.get("direction"):
        base_query += " AND m.direction = :direction"
        params["direction"] = filters["direction"]

    if filters.get("start_date"):
        base_query += " AND DATE(m.timestamp) >= :start_date"
        params["start_date"] = filters["start_date"]

    if filters.get("end_date"):
        base_query += " AND DATE(m.timestamp) <= :end_date"
        params["end_date"] = filters["end_date"]

    base_query += " ORDER BY m.timestamp DESC LIMIT 200"

    query = text(base_query)
    results = db.execute(query, params).mappings().all()
    return list(results)