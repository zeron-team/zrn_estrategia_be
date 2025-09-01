# app/crud/auth_queries.py

from sqlalchemy.orm import Session
from sqlalchemy import text

def get_user(db: Session, username: str) -> dict | None:
    """Busca un usuario por su nombre de usuario en la tabla crm_users."""
    query = text("SELECT username, hashed_password, role FROM crm_users WHERE username = :username")
    result = db.execute(query, {"username": username}).first()
    if result:
        return result._asdict()
    return None