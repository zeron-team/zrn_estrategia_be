from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class CrmUser(Base):
    __tablename__ = "crm_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    name = Column(String(50), nullable=True)
    lastname = Column(String(50), nullable=True)
    phone_number = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(String(50), nullable=False)
    message_body = Column(Text)
    direction = Column(Enum('incoming', 'outgoing', name='message_direction'), nullable=False)
    to_id = Column(String(50), nullable=True)
    template_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(50), unique=True, index=True)
    # Add other student fields if necessary

class CaseAction(Base):
    __tablename__ = "case_actions"

    id = Column(Integer, primary_key=True, index=True)
    student_phone = Column(String(50), index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True) # New field
    action_type = Column(String(50), index=True)  # e.g., 'case_taken', 'manual_contact'
    user_id = Column(Integer, ForeignKey("crm_users.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class ActionNote(Base):
    __tablename__ = "action_notes"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(Integer, ForeignKey("case_actions.id"))
    note = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("crm_users.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class DashboardAlert(Base):
    __tablename__ = "dashboard_alerts"

    id = Column(Integer, primary_key=True, index=True)
    student_phone = Column(String(50), index=True, nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    alert_type = Column(String(50), nullable=False) # e.g., 'human_intervention_needed', 'recovery_reminder'
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    is_resolved = Column(Boolean, default=False)