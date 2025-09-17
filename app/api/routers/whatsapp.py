# app/api/routers/whatsapp.py

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Query
from sqlalchemy.orm import Session
from twilio.rest import Client
from twilio.request_validator import RequestValidator
import os

from app.db.session import get_chatbot_db, get_moodle_db
from app.core.config import settings
from app.crud import crud_operations, moodle_queries
from app.schemas import message as message_schema
from app.flows import flow_manager # Import flow_manager

router = APIRouter()

validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

@router.post("/webhook")
async def whatsapp_webhook(request: Request, chatbot_db: Session = Depends(get_chatbot_db), moodle_db: Session = Depends(get_moodle_db)):
    print("--- INCOMING MESSAGE ---")
    try:
        # Manually parse the form data
        form = await request.form()
        from_number = form.get("From")
        body = form.get("Body")

        print(f"From: {from_number}")
        print(f"Body: {body}")

        # Twilio signature validation
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        if not validator.validate(url, dict(form), signature):
            print("❌ Invalid Twilio signature.")
            raise HTTPException(status_code=400, detail="Invalid Twilio signature")
        
        print("✅ Twilio signature validated.")

        # 1. Guarda el mensaje entrante en nuestra DB
        print("Saving incoming message...")
        incoming_message = message_schema.MessageCreate(sender_id=from_number, message_body=body, direction='incoming')
        crud_operations.create_message(chatbot_db, message=incoming_message)
        print("✅ Incoming message saved.")

        # 2. Busca al alumno por su número de teléfono en la DB de Moodle
        print(f"Searching for student with phone: {from_number}")
        student = moodle_queries.get_student_by_phone(moodle_db, phone_number=from_number)

        # --- TEST MODE ---
        if not student and settings.TEST_MODE_PHONE_NUMBER and from_number == settings.TEST_MODE_PHONE_NUMBER:
            print(f"--- RUNNING IN TEST MODE FOR NUMBER: {from_number} ---")
            student = {
                "moodle_user_id": 999,
                "full_name": "Test User"
            }
        # --- END TEST MODE ---

        print(f"Student found: {student}")

        reply_text = ""
        next_node_id = None

        if not student:
            reply_text = "Hola. No hemos podido identificarte en nuestro sistema. Por favor, contacta con administración."
        else:
            flows = flow_manager.load_flows()
            
            # Get the last outgoing message to determine context
            last_outgoing_message = crud_operations.get_last_outgoing_message(chatbot_db, to_id=from_number)

            current_node_id = None
            if last_outgoing_message and last_outgoing_message.template_id:
                current_node_id = last_outgoing_message.template_id
            
            print(f"Current node ID: {current_node_id}")

            active_flow = None
            if current_node_id:
                for f in flows:
                    if any(node['id'] == current_node_id for node in f.get('nodes', [])):
                        active_flow = f
                        break
            
            if not active_flow:
                # Fallback for cases where the conversation starts without a template_id, 
                # or the node is not found in any active flow.
                # This part might need more sophisticated logic depending on desired behavior.
                reply_text = "No hemos podido encontrar un flujo de conversación activo. Por favor, contacta a soporte."
            else:
                next_node = None
                next_node_id = None

                if current_node_id:
                    outgoing_edges = [edge for edge in active_flow.get("edges", []) if edge["source"] == current_node_id]
                    
                    # Find the next node by matching the user's response with the edge's labelText
                    for edge in outgoing_edges:
                        if edge.get("labelText", "").lower() == body.strip().lower():
                            next_node_id = edge["target"]
                            break # Found a match

                    if next_node_id:
                        next_node = next((node for node in active_flow.get("nodes", []) if node["id"] == next_node_id), None)

                if not next_node:
                    reply_text = "Lo siento, no entendí tu respuesta. Por favor, intenta de nuevo o contacta con administración."
                else:
                    # We have the next node, so we can format the reply
                    student_name = student["full_name"].split(" ")[0]
                    course_name = moodle_queries.get_course_name_by_id(moodle_db, settings.TARGET_COURSE_ID) or "este curso"
                    # recovery_date would need to be fetched from Moodle if available
                    recovery_date = "a confirmar" 

                    try:
                        reply_text = next_node["data"]["label"].format(
                            student_name=student_name, 
                            course_name=course_name,
                            recovery_date=recovery_date
                        )
                    except KeyError as e:
                        print(f"KeyError formatting reply: {e}. Using label as is.")
                        reply_text = next_node["data"]["label"]

                    next_node_id = next_node["id"]

                    # Check for alert condition (DESAPROBADO_2C)
                    if next_node_id == "DESAPROBADO_2C":
                        alert_description = f"Student {student['full_name']} ({from_number}) responded 'C' to failed exam follow-up. Needs tutor contact."
                        alert_data = DashboardAlertCreate(
                            student_phone=from_number,
                            alert_type="human_intervention_needed",
                            description=alert_description
                        )
                        crud_operations.create_dashboard_alert(chatbot_db, alert=alert_data)
                        print("✅ Dashboard alert created for human intervention.")

        print(f"Reply text: {reply_text}")

        # 5. Envía la respuesta por WhatsApp
        print("Sending reply...")
        outgoing_twilio_message = twilio_client.messages.create(
            from_=settings.TWILIO_FROM_NUMBER,
            body=reply_text,
            to=from_number
        )
        print("✅ Reply sent.")

        # 6. Guarda el mensaje saliente en nuestra DB
        print("Saving outgoing message...")
        outgoing_message = message_schema.MessageCreate(
            sender_id=settings.TWILIO_FROM_NUMBER,
            message_body=reply_text,
            direction='outgoing',
            to_id=from_number,
            template_id=next_node_id # Save the next node ID as template_id
        )
        crud_operations.create_message(chatbot_db, message=outgoing_message)
        print("✅ Outgoing message saved.")

        return {"status": "success", "sid": outgoing_twilio_message.sid}

    except Exception as e:
        print(f"❌❌❌ Webhook Error: {e} ❌❌❌")
        print(f"Request: {request}")
        print(f"Headers: {request.headers}")
        body = await request.body()
        print(f"Body: {body}")
        return {"status": "error"}