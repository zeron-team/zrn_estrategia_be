from sqlalchemy import Column, Integer, String, Text, Enum
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(String(50), nullable=False)
    message_body = Column(Text)
    direction = Column(Enum('incoming', 'outgoing', name='message_direction'), nullable=False)
    to_id = Column(String(50), nullable=True)