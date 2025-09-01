# app/schemas/notification.py

from pydantic import BaseModel

class NotificationRequest(BaseModel):
    moodle_user_id: int