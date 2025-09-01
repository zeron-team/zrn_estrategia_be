# app/api/deps.py

from app.services.interfaces import IMoodleService, IWhatsAppService
from app.services.moodle_service import MoodleService
from app.services.whatsapp_service import WhatsAppService # (Debes crear este archivo similar a MoodleService)

# Principio de Inversión de Dependencias (D):
# FastAPI inyectará una instancia de MoodleService donde se requiera IMoodleService.
# Si mañana creamos un MockMoodleService para tests, solo cambiamos esta línea.
def get_moodle_service() -> IMoodleService:
    return MoodleService()

def get_whatsapp_service() -> IWhatsAppService:
    # Asumimos que WhatsAppService está implementado
    return WhatsAppService()