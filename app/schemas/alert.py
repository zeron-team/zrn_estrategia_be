from pydantic import BaseModel
from typing import Optional

class DashboardAlertCreate(BaseModel):
    student_phone: str
    message_id: Optional[int] = None
    alert_type: str
    description: Optional[str] = None
    is_resolved: Optional[bool] = False
