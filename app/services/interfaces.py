# app/services/interfaces.py

from abc import ABC, abstractmethod

# Principio de Segregación de Interfaces (I) y Dependencia (D)
# Los routers dependerán de estas abstracciones, no de las clases concretas.

class IMoodleService(ABC):
    @abstractmethod
    def get_student_grade(self, user_id: int) -> float | None:
        """Obtiene la calificación final de un estudiante en un curso."""
        pass

class IWhatsAppService(ABC):
    @abstractmethod
    def send_message(self, to: str, body: str) -> bool:
        """Envía un mensaje de WhatsApp."""
        pass