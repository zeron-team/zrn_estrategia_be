# app/api/routers/whatsapp.py

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Query
from sqlalchemy.orm import Session
from twilio.rest import Client

from app.db.session import get_chatbot_db, get_moodle_db
from app.core.config import settings
from app.crud import crud_operations, moodle_queries
from app.schemas import message as message_schema

router = APIRouter()

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# --- NUEVO ENDPOINT GET PARA LA VERIFICACIÓN DE META/WHATSAPP ---
@router.get("/webhook")
def verify_webhook(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Este endpoint maneja el desafío de verificación que envía Meta
    para confirmar que la URL del webhook te pertenece.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        print("✅ Webhook verificado exitosamente.")
        return int(hub_challenge)
    else:
        print("❌ Falló la verificación del webhook.")
        raise HTTPException(status_code=403, detail="Verify token does not match or mode is not subscribe")


@router.post("/webhook")
def whatsapp_webhook(
        chatbot_db: Session = Depends(get_chatbot_db),
        moodle_db: Session = Depends(get_moodle_db),
        From: str = Form(...),
        Body: str = Form(...),
):
    # 1. Guarda el mensaje entrante en nuestra DB
    incoming_message = message_schema.MessageCreate(sender_id=From, message_body=Body, direction='incoming')
    crud_operations.create_message(chatbot_db, message=incoming_message)

    # 2. Busca al alumno por su número de teléfono en nuestra DB para obtener su Moodle ID
    student = moodle_queries.get_student_by_phone(chatbot_db, phone_number=From)

    if not student:
        reply_text = "Hola. No hemos podido identificarte en nuestro sistema. Por favor, contacta con administración."
    else:
        moodle_user_id = student["moodle_user_id"]
        student_name = student["full_name"].split(" ")[0]  # Tomamos el primer nombre

        # 3. Con el Moodle ID, consulta la nota en la DB de Moodle
        final_grade = moodle_queries.get_final_grade(moodle_db, user_id=moodle_user_id)

        # 4. Construye la respuesta basada en la nota
        if final_grade is None:
            reply_text = f"Hola {student_name}. Parece que no tienes una nota final registrada para este curso. ¿Te has presentado a la evaluación? \n1. Sí, me presenté\n2. No, tuve un problema\n3. Necesito ayuda"
        elif final_grade >= 4.0:  # Umbral de aprobación (ajustar si es necesario)
            reply_text = f"¡Felicitaciones, {student_name}! Has aprobado el curso con una nota final de {final_grade}. ¡Excelente trabajo! 🥳"
        else:
            reply_text = f"Hola {student_name}. Tu nota final es {final_grade}. Para ayudarte a mejorar, ¿cuál crees que fue el principal motivo? 🤔\n1. El examen fue muy difícil\n2. No tuve tiempo para estudiar\n3. No entendí algunos temas"

    # 5. Envía la respuesta por WhatsApp
    try:
        outgoing_twilio_message = twilio_client.messages.create(
            from_=settings.TWILIO_FROM_NUMBER,
            body=reply_text,
            to=From
        )
        # 6. Guarda el mensaje saliente en nuestra DB
        outgoing_message = message_schema.MessageCreate(
            sender_id=settings.TWILIO_FROM_NUMBER,
            message_body=reply_text,
            direction='outgoing',
            to_id=From  # <-- AÑADE ESTA LÍNEA
        )
        crud_operations.create_message(chatbot_db, message=outgoing_message)
        return {"status": "success", "sid": outgoing_twilio_message.sid}
    except Exception as e:
        print(f"Error al enviar mensaje de respuesta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

