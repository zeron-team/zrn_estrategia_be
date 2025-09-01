# scripts/create_first_user.py

import sys
import os
import getpass
import bcrypt

# Añadimos la ruta raíz del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocalChatbot
from sqlalchemy import text


def create_user():
    print("--- Creación del Primer Usuario Administrador (usando bcrypt directo) ---")

    username = input("Ingresa el nombre de usuario: ")
    password = getpass.getpass("Ingresa la contraseña: ")

    # Ciframos la contraseña con bcrypt directamente
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password_bytes = bcrypt.hashpw(password_bytes, salt)
    # Guardamos el hash como una cadena de texto en la base de datos
    hashed_password_str = hashed_password_bytes.decode('utf-8')

    db = SessionLocalChatbot()
    try:
        query = text(
            "INSERT INTO crm_users (username, hashed_password, role) VALUES (:user, :pwd, :role)"
        )
        db.execute(query, {"user": username, "pwd": hashed_password_str, "role": "admin"})
        db.commit()
        print(f"✅ ¡Usuario '{username}' creado exitosamente en la base de datos!")
    except Exception as e:
        print(f"❌ Error al crear el usuario: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_user()