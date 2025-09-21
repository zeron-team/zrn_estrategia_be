# app/scripts/bootstrap_chatbot_db.py
from __future__ import annotations

from sqlalchemy import text
import bcrypt

from app.db.session import get_chatbot_db

DDL = text("""
CREATE TABLE IF NOT EXISTS crm_users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'admin',
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

def main():
    # Abrimos sesión usando la misma dependencia que usa FastAPI
    db_gen = get_chatbot_db()
    db = next(db_gen)
    try:
        # 1) Crear tabla si no existe
        db.execute(DDL)
        db.commit()

        # 2) Si no hay admin, lo creamos (admin / admin123)
        row = db.execute(text("SELECT id FROM crm_users WHERE username=:u"), {"u": "admin"}).first()
        if not row:
            raw_pwd = "admin123"
            hashed = bcrypt.hashpw(raw_pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            db.execute(
                text("INSERT INTO crm_users (username, hashed_password, role, is_active) "
                     "VALUES (:u, :p, :r, 1)"),
                {"u": "admin", "p": hashed, "r": "admin"},
            )
            db.commit()
            print("✅ Tabla 'crm_users' creada y usuario admin/admin123 cargado.")
        else:
            print("ℹ️  'crm_users' ya existe y hay un usuario 'admin'.")
    finally:
        db.close()
        # cerrar el generator limpio
        try:
            next(db_gen)
        except StopIteration:
            pass

if __name__ == "__main__":
    main()