# scripts/send_passed_notifications.py

import sys
import os
import time
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from twilio.rest import Client

# Añadimos la ruta raíz del proyecto al path de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ahora podemos importar nuestros módulos
from app.db.session import SessionLocalChatbot, SessionLocalMoodle
from app.core.config import settings
from app.schemas.message import MessageCreate
from app.crud.crud_operations import create_message
from app.flows import flow_manager

FROM = settings.TWILIO_FROM_NUMBER

def get_recent_grades(moodle_db: Session, hours_ago: int = 24):
    start_time = datetime.now() - timedelta(hours=hours_ago)
    start_timestamp = int(start_time.timestamp())
    query = text("""
        SELECT u.id AS user_id, u.firstname, c.fullname AS course_name, gg.finalgrade
        FROM mdl_grade_grades AS gg
        JOIN mdl_grade_items AS gi ON gg.itemid = gi.id
        JOIN mdl_user AS u ON gg.userid = u.id
        JOIN mdl_course AS c ON gi.courseid = c.id
        WHERE gi.itemtype = 'course' AND gg.finalgrade IS NOT NULL AND gg.timemodified >= :start_timestamp
    """)
    results = moodle_db.execute(query, {"start_timestamp": start_timestamp}).mappings().all()
    return results

def send_passed_notifications():
    """
    Obtiene las notas de los alumnos aprobados y les envía una notificación.
    """
    print("🤖 Iniciando script de notificación para alumnos APROBADOS...")

    DELAY_SECONDS = 5
    TEST_PHONE_NUMBER = settings.TEST_PHONE_NUMBER
    if not TEST_PHONE_NUMBER:
        print("❌ La variable de entorno TEST_PHONE_NUMBER no está configurada. Saliendo.")
        return
    print(f"🔒 MODO SEGURO: Todos los mensajes se enviarán a {TEST_PHONE_NUMBER}")

    chatbot_db = SessionLocalChatbot()
    moodle_db = SessionLocalMoodle()
    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        flows = flow_manager.load_flows()
        flow_info = {"flow_name": "Alumno APROBADO", "node_id": "APROBADO_1"}
        status = 'passed'

        recent_grades = get_recent_grades(moodle_db)

        if not recent_grades:
            print("✅ No se encontraron calificaciones nuevas. Finalizando.")
            return

        print(f"📊 Se encontraron {len(recent_grades)} calificaciones nuevas para procesar.")

        for grade_info in recent_grades:
            student_name = grade_info['firstname']
            course_name = grade_info['course_name']
            final_grade = float(grade_info['finalgrade'])

            # This script only handles passed students (grade >= 6)
            if final_grade < 6:
                continue

            print(f"Processing PASSED student: {student_name}")

            target_flow = next((f for f in flows if f.get("name") == flow_info["flow_name"]), None)
            target_node_id = flow_info["node_id"]

            if not target_flow:
                print(f"❌ Flujo '{flow_info['flow_name']}' no encontrado. Saltando a {student_name}.")
                continue
            
            target_node = next((node for node in target_flow["nodes"] if node["id"] == target_node_id), None)

            if not target_node:
                print(f"❌ Nodo inicial '{target_node_id}' no encontrado. Saltando a {student_name}.")
                continue

            template_sid = target_node["data"].get("template_sid")
            if not template_sid:
                print(f"❌ El nodo inicial '{target_node_id}' no tiene un template_sid. Saltando a {student_name}.")
                continue

            message_body_for_db = target_node["data"]["label"].format(
                student_name=student_name, 
                course_name=course_name,
                recovery_date="a confirmar"
            )

            try:
                print(f"✉️  Enviando mensaje de '{status}' a {student_name}...")
                content_variables = {"1": student_name, "2": course_name}
                message = twilio_client.messages.create(
                    from_=FROM,
                    to=TEST_PHONE_NUMBER,
                    content_sid=template_sid,
                    content_variables=json.dumps(content_variables)
                )
                print("   -> Mensaje enviado a la API de Twilio.")
            except Exception as e:
                print(f"❌ Error al enviar mensaje a {student_name} vía Twilio: {e}")
                continue

            try:
                outgoing_message = MessageCreate(
                    sender_id=FROM,
                    to_id=TEST_PHONE_NUMBER,
                    message_body=message_body_for_db,
                    direction='outgoing',
                    template_id=template_sid
                )
                create_message(chatbot_db, message=outgoing_message)
                print("   -> Registro guardado en la base de datos.")
            except Exception as e:
                print(f"❌ Error al guardar el mensaje en la base de datos: {e}")

            print(f"--- Pausando por {DELAY_SECONDS} segundos... ---")
            time.sleep(DELAY_SECONDS)

    finally:
        chatbot_db.close()
        moodle_db.close()
        print("✅ Script finalizado.")

if __name__ == "__main__":
    send_passed_notifications()
