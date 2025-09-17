from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from app.schemas.user import UserCreate, UserUpdate
from app.security import get_password_hash

def get_user_by_username(db: Session, username: str) -> Optional[Dict[str, Any]]:
    query = text("SELECT * FROM crm_users WHERE username = :username")
    result = db.execute(query, {"username": username}).first()
    return result._asdict() if result else None

def get_user_by_id(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    query = text("SELECT * FROM crm_users WHERE id = :user_id")
    result = db.execute(query, {"user_id": user_id}).first()
    return result._asdict() if result else None

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    query = text("SELECT id, username, name, lastname, phone_number, email, role FROM crm_users ORDER BY id LIMIT :limit OFFSET :skip")
    results = db.execute(query, {"limit": limit, "skip": skip}).all()
    return [r._asdict() for r in results]

def create_user(db: Session, user: UserCreate) -> Dict[str, Any]:
    hashed_password = get_password_hash(user.password)
    query = text("""
        INSERT INTO crm_users (username, name, lastname, phone_number, email, hashed_password, role)
        VALUES (:username, :name, :lastname, :phone_number, :email, :hashed_password, :role)
    """)
    params = user.dict()
    params.pop('password')
    params['hashed_password'] = hashed_password
    params['role'] = 'user' # Default role
    db.execute(query, params)
    db.commit()
    return get_user_by_username(db, user.username)

def update_user(db: Session, user_id: int, user: UserUpdate) -> Optional[Dict[str, Any]]:
    fields_to_update = user.dict(exclude_unset=True)
    if 'password' in fields_to_update:
        if fields_to_update['password']:
            fields_to_update['hashed_password'] = get_password_hash(fields_to_update.pop('password'))
        else:
            fields_to_update.pop('password')

    if not fields_to_update:
        return get_user_by_id(db, user_id)

    set_clause = ", ".join([f"{key} = :{key}" for key in fields_to_update.keys()])
    query = text(f"UPDATE crm_users SET {set_clause} WHERE id = :user_id")
    params = {**fields_to_update, "user_id": user_id}
    db.execute(query, params)
    db.commit()
    return get_user_by_id(db, user_id)

def delete_user(db: Session, user_id: int) -> bool:
    query = text("DELETE FROM crm_users WHERE id = :user_id")
    result = db.execute(query, {"user_id": user_id})
    db.commit()
    return result.rowcount > 0
