# app/api/routers/predictive.py

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.session import get_moodle_db
from app.crud import analytics_queries as aq

router = APIRouter()

# ---------- Response Models ----------
class RiskByCourse(BaseModel):
    course_id: int
    course_name: str | None = None
    at_risk_count: int = 0
    total_learners: int = 0
    risk_rate: float = 0.0

class TimePoint(BaseModel):
    period: str
    at_risk_count: int
    is_forecast: bool = False

class HeatmapCell(BaseModel):
    course_id: int
    course_name: str | None = None
    period: str
    at_risk_count: int

class AtRiskItem(BaseModel):
    user_id: int
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None
    course_id: int
    course_name: str | None = None
    failed_count: int
    absent_count: int
    last_period: str | None = None
    risk_score: int = Field(ge=0, le=100)
    bucket: str

# ---------- Endpoints ----------
@router.get("/predictive/overview/risk_by_course", response_model=List[RiskByCourse])
def predictive_risk_by_course(
    min_score: int = Query(50, ge=0, le=100),
    limit: int = Query(12, ge=1, le=200),
    db: Session = Depends(get_moodle_db),
):
    """
    Top courses by count of at-risk (user, course) pairs (score >= min_score).
    """
    return aq.get_risk_by_course(db, min_score=min_score, limit=limit)

@router.get("/predictive/overview/risk_time_series", response_model=List[TimePoint])
def predictive_risk_time_series(
    min_score: int = Query(50, ge=0, le=100),
    months_back: int = Query(12, ge=1, le=36),
    include_forecast: bool = Query(True),
    forecast_horizon: int = Query(3, ge=1, le=6),
    db: Session = Depends(get_moodle_db),
):
    """
    Monthly at-risk counts. Optionally appends a simple moving-average forecast.
    """
    return aq.get_risk_time_series(db,
                                   min_score=min_score,
                                   months_back=months_back,
                                   include_forecast=include_forecast,
                                   forecast_horizon=forecast_horizon)

@router.get("/predictive/overview/heatmap", response_model=List[HeatmapCell])
def predictive_heatmap(
    min_score: int = Query(50, ge=0, le=100),
    months_back: int = Query(6, ge=1, le=24),
    top_courses: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_moodle_db),
):
    """
    Heatmap data: (course, period) -> at_risk_count for the top N courses by total risk.
    """
    return aq.get_risk_heatmap(db,
                               min_score=min_score,
                               months_back=months_back,
                               top_courses=top_courses)

@router.get("/predictive/at_risk", response_model=List[AtRiskItem])
def predictive_at_risk(
    min_score: int = Query(50, ge=0, le=100),
    course_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None, description="YYYY-MM"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_moodle_db),
):
    """
    Detailed at-risk rows (student-course). Supports filters by course_id and/or period.
    """
    return aq.get_at_risk_students(db,
                                   min_score=min_score,
                                   course_id=course_id,
                                   period=period,
                                   limit=limit)