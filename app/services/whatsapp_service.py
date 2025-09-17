# app/services/whatsapp_service.py

import requests
from app.core.config import settings
from .interfaces import IWhatsAppService

class WhatsAppService(IWhatsAppService):
    def send_message(self, to: str, body: str) -> bool:
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        }
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        try:
            response = requests.post(settings.WHATSAPP_API_URL, headers=headers, json=data)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Error connecting to WhatsApp API: {e}")
            return False
