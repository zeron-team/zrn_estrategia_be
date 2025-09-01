#app/schemas/kpi.py

from pydantic import BaseModel

class KpiData(BaseModel):
    total_contacted: int
    approved: int
    disapproved: int
    total_interactions: int