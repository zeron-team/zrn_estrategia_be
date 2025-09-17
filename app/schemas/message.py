# app/schemas/message.py

from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

class MessageBase(BaseModel):
    sender_id: str
    message_body: str | None = None
    to_id: Optional[str] = None
    template_id: Optional[str] = None

class MessageCreate(MessageBase):
    direction: Literal['incoming', 'outgoing']

class MessageInDB(MessageCreate):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True # Permite que Pydantic lea desde objetos de base de datos