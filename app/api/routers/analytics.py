# app/api/routers/analytics.py
from __future__ import annotations

from typing import Dict, Any, List, Optional, Literal

from fastapi import APIRouter, Depends, Query, Path
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from fastapi_cache.decorator import cache

from app.db.session import get_moodle_db
from app.crud import analytics_queries as aq

router = APIRouter()

# ---------- Cache TTLs (seconds) ----------
KPI_CACHE_SEC = 300
COURSE_CACHE_SEC = 300
DETAILS_CACHE_SEC = 180

# -------------------------
# Pydantic response models
# -------------------------

class PeriodStatusItem(BaseModel):
    period: str
    PASSED: int
    FAILED: int
    ABSENT: int


class CourseAnalytics(BaseModel):
    course_name: str
    PASSED: int
    FAILED: int
    ABSENT: int


class NotesAnalyticsKPIs(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    total_notes: int
    notes_by_status: Dict[str, int]
    notes_by_status_over_time: List[PeriodStatusItem]

    # Buckets (exposed under two keys for front-end compatibility)
    failure_absence_buckets: Dict[str, int]
    student_failure_absence_buckets: Dict[str, int]


class BucketDetailRow(BaseModel):
    user_id: int
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[str] = None
    course_id: int
    course_name: Optional[str] = None  # included for the table
    failed_count: int
    absent_count: int


BucketKey = Literal[
    "fail_1_same_course",
    "fail_2_same_course",
    "fail_gt_2_same_course",
    "absent_1_same_course",
    "absent_2_same_course",
    "absent_1_fail_1_same_course",
    "absent_gt_1_fail_gt_1_same_course",
]

# -------------------------
# Routes
# -------------------------

@router.get(
    "/notes/analytics/kpis",
    response_model=NotesAnalyticsKPIs,
    summary="KPIs y series para notas",
    response_description="Totales, breakdown por estado y serie temporal, más buckets de fallas/ausencias.",
)
@cache(expire=60)
def get_notes_analytics_kpis(
    db: Session = Depends(get_moodle_db),
    period: Literal["month", "day"] = Query("month", description="Granularidad de la serie temporal"),
) -> NotesAnalyticsKPIs:
    total_notes = aq.get_total_notes(db)
    notes_by_status = aq.get_notes_by_status(db)
    over_time_raw = aq.get_notes_by_status_over_time(db, period=period)

    over_time: List[PeriodStatusItem] = [
        PeriodStatusItem(
            period=row.get("period", ""),
            PASSED=int(row.get("PASSED", 0) or 0),
            FAILED=int(row.get("FAILED", 0) or 0),
            ABSENT=int(row.get("ABSENT", 0) or 0),
        )
        for row in (over_time_raw or [])
    ]

    buckets = aq.get_failure_absence_analytics(db)

    return NotesAnalyticsKPIs(
        total_notes=int(total_notes or 0),
        notes_by_status={k: int(v or 0) for k, v in (notes_by_status or {}).items()},
        notes_by_status_over_time=over_time,
        failure_absence_buckets=buckets,
        student_failure_absence_buckets=buckets,  # same dict, two keys for FE resilience
    )


@router.get(
    "/notes/analytics/courses_by_month/{month}",
    response_model=List[CourseAnalytics],
    summary="Detalle por curso para un mes",
    response_description="Lista de cursos con conteos PASSED / FAILED / ABSENT para el mes dado.",
)
@cache(expire=COURSE_CACHE_SEC)
def get_courses_by_month_analytics(
    month: str = Path(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Mes en formato YYYY-MM"),
    limit: Optional[int] = Query(None, ge=1, le=200, description="Máximo de cursos a retornar"),
    db: Session = Depends(get_moodle_db),
) -> List[CourseAnalytics]:
    rows = aq.get_course_details_for_month(db, month=month, limit=limit)
    return [
        CourseAnalytics(
            course_name=r.get("course_name", ""),
            PASSED=int(r.get("PASSED", 0) or 0),
            FAILED=int(r.get("FAILED", 0) or 0),
            ABSENT=int(r.get("ABSENT", 0) or 0),
        )
        for r in rows
    ]


@router.get(
    "/notes/analytics/buckets/detail",
    response_model=List[BucketDetailRow],
    summary="Drill-down de alumnos/curso por bucket",
    response_description="Filas por alumno y curso con sus contadores de reprobados/ausentes.",
)
@cache(expire=DETAILS_CACHE_SEC)
def get_bucket_details(
    bucket: BucketKey = Query(..., description="Clave del bucket a expandir"),
    limit: int = Query(300, ge=1, le=2000, description="Límite de filas"),
    offset: int = Query(0, ge=0, description="Desplazamiento (paginación simple)"),
    db: Session = Depends(get_moodle_db),
) -> List[BucketDetailRow]:
    """
    Devuelve filas (alumno, curso) que pertenecen al bucket solicitado.
    Se pagina con `limit` y `offset` para evitar respuestas muy grandes.
    """
    rows = aq.get_bucket_details(db, bucket)  # devuelve lista completa
    if offset or limit:
        rows = rows[offset : offset + limit]
    return [BucketDetailRow(**r) for r in rows]