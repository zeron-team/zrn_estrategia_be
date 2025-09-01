# app/api/routers/notifications.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from twilio.rest import Client

from app.db.session import get_chatbot_db, get_moodle_db
from app.core.config import settings
from app.crud import crud_operations, moodle_queries
from app.schemas import message as message_schema
from app.schemas.notification import NotificationRequest # Crearemos este schema si no existe

router = APIRouter()

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

@router.post("/send-grade")
def send_grade_notification(
    request: NotificationRequest,
    chatbot_db: Session = Depends(get_chatbot_db),
    moodle_db: Session = Depends(get_moodle_db),
):
    """
    Inicia una notificación proactiva para enviar la nota a un alumno específico.
    """
    moodle_user_id = request.moodle_user_id

    student_phone = moodle_queries.get_phone_by_moodle_id(chatbot_db, moodle_user_id=moodle_user_id)
    if not student_phone:
        raise HTTPException(status_code=404, detail=f"No se encontró el número de teléfono para el usuario de Moodle con ID {moodle_user_id}")

    final_grade = moodle_queries.get_final_grade(moodle_db, user_id=moodle_user_id)
    if final_grade is None:
        raise HTTPException(status_code=404, detail=f"No se encontró una nota final para el usuario de Moodle con ID {moodle_user_id}")

    if final_grade >= 6.0:
        reply_text = f"¡Hola! Te informamos que tu nota final del curso es {final_grade}. ¡Has aprobado! Felicitaciones."
    else:
        reply_text = f"Hola, te informamos que tu nota final del curso es {final_grade}. Contacta a un tutor para revisar tus opciones."

    try:
        outgoing_twilio_message = twilio_client.messages.create(
            from_=settings.TWILIO_FROM_NUMBER, body=reply_text, to=student_phone
        )
        outgoing_message = message_schema.MessageCreate(sender_id=settings.TWILIO_FROM_NUMBER, message_body=reply_text, direction='outgoing')
        crud_operations.create_message(chatbot_db, message=outgoing_message)

        return {"status": "success", "detail": f"Mensaje enviado a {student_phone}", "sid": outgoing_twilio_message.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar mensaje vía Twilio: {str(e)}")