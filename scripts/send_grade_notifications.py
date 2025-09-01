# scripts/send_grade_notifications.py

import sys
import os
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from twilio.rest import Client

# Añadimos la ruta raíz del proyecto al path de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ahora podemos importar nuestros módulos
from app.db.session import SessionLocalChatbot, SessionLocalMoodle
from app.core.config import settings
from app.crud.moodle_queries import get_phone_by_moodle_id
from app.schemas.message import MessageCreate # Importamos el schema
from app.crud.crud_operations import create_message


def get_recent_grades(moodle_db: Session,
                      hours_ago: int = 720):  # --- CAMBIO PARA PRUEBAS: de 24 a 720 horas (aprox. 1 mes)
    """
    Busca en la DB de Moodle las calificaciones finales de cursos que
    fueron modificadas en las últimas 'hours_ago' horas.
    """
    # --- CAMBIO PARA PRUEBAS: La lógica de 'último mes' se controla cambiando el valor por defecto de 'hours_ago'
    # start_time = datetime.now() - timedelta(hours=24) # <-- Lógica original comentada
    start_time = datetime.now() - timedelta(hours=hours_ago)
    start_timestamp = int(start_time.timestamp())

    query = text("""
        SELECT
            u.id AS user_id,
            u.firstname,
            c.fullname AS course_name,
            gg.finalgrade
        FROM
            mdl_grade_grades AS gg
        JOIN
            mdl_grade_items AS gi ON gg.itemid = gi.id
        JOIN
            mdl_user AS u ON gg.userid = u.id
        JOIN
            mdl_course AS c ON gi.courseid = c.id
        WHERE
            gi.itemtype = 'course'
            AND gg.finalgrade IS NOT NULL
            AND gg.timemodified >= :start_timestamp
    """)

    results = moodle_db.execute(query, {"start_timestamp": start_timestamp}).mappings().all()
    return results


def send_notifications():
    """
    Función principal que obtiene las notas y envía los mensajes.
    """
    print("🤖 Iniciando script de notificación...")

    # ... (código de configuración de delay, número de prueba, etc. se mantiene igual) ...
    DELAY_SECONDS = 5
    TEST_PHONE_NUMBER = 'whatsapp:+5491135665266'
    print(f"🔒 MODO SEGURO: Todos los mensajes se enviarán a {TEST_PHONE_NUMBER}")

    chatbot_db = SessionLocalChatbot()
    moodle_db = SessionLocalMoodle()

    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        recent_grades = get_recent_grades(moodle_db)

        if not recent_grades:
            print("✅ No se encontraron calificaciones nuevas. Finalizando.")
            return

        print(f"📊 Se encontraron {len(recent_grades)} calificaciones nuevas para notificar.")

        for grade_info in recent_grades:
            # ... (código para construir el message_body se mantiene igual) ...
            student_name = grade_info['firstname']
            course_name = grade_info['course_name']
            final_grade = round(float(grade_info['finalgrade']), 2)

            message_body = ""
            if final_grade >= 6:
                message_body = f"¡Felicitaciones, {student_name}! 🎉 Has aprobado el curso '{course_name}' con una nota final de {final_grade}."
            else:
                message_body = f"Hola {student_name}. Tu nota final en '{course_name}' es {final_grade}. ¿Cuál crees que fue el motivo? Responde A, B o C..."

            # --- LÓGICA CORREGIDA ---

            # 1. Intentamos enviar el mensaje por Twilio
            try:
                print(f"✉️  Enviando mensaje a {student_name}...")
                twilio_client.messages.create(
                    from_=settings.TWILIO_FROM_NUMBER,
                    body=message_body,
                    to=TEST_PHONE_NUMBER
                )
                print("   -> Mensaje enviado a la API de Twilio.")
            except Exception as e:
                print(f"❌ Error al enviar mensaje a {student_name} vía Twilio: {e}")
                continue  # Si falla el envío, saltamos al siguiente alumno

            # 2. Si el envío fue exitoso, AHORA guardamos en la base de datos
            try:
                outgoing_message = MessageCreate(
                    sender_id=settings.TWILIO_FROM_NUMBER,
                    message_body=message_body,
                    direction='outgoing'
                    # El timestamp lo añade la DB por defecto
                )
                create_message(chatbot_db, message=outgoing_message)
                print("   -> Registro guardado en la base de datos.")
            except Exception as e:
                print(f"❌ Error al guardar el mensaje en la base de datos: {e}")

            # 3. Pausamos antes del siguiente
            print(f"--- Pausando por {DELAY_SECONDS} segundos... ---")
            time.sleep(DELAY_SECONDS)
            # --- FIN DE LÓGICA CORREGIDA ---

    finally:
        chatbot_db.close()
        moodle_db.close()
        print("✅ Script finalizado.")


if __name__ == "__main__":
    send_notifications()