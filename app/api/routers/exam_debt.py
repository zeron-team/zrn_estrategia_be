# app/api/routers/exam_debt.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud import analytics_queries as aq

# Igual que el resto de tus routers: el prefix de este módulo es /exams/debt.
router = APIRouter(prefix="/exams/debt", tags=["Exámenes Adeudados"])

# --- Summary global ---
@router.get("/summary")
@router.get("/summary/")
def exams_debt_summary(db: Session = Depends(get_db)):
    # Tu analytics_queries actual no recibe filtros aquí
    return aq.get_exam_debt_summary(db)

# --- Summary agrupado por curso/carrera ---
@router.get("/summary_by_course")
@router.get("/summary_by_course/")
def exams_debt_summary_by_course(db: Session = Depends(get_db)):
    # Tu analytics_queries actual no recibe filtros aquí
    return aq.get_exam_debt_summary_by_course(db)

# --- Detalle por bucket ---
@router.get("/details")
@router.get("/details/")
def exams_debt_details(
    bucket: str = Query("1", description="Uno de: 0, 1, 2, gt2"),
    db: Session = Depends(get_db),
):
    b = str(bucket).lower()
    if b not in {"0", "1", "2", "gt2"}:
        raise HTTPException(status_code=400, detail="bucket debe ser 0, 1, 2 o gt2")
    # Tu analytics_queries actual no recibe filtros aquí
    return aq.get_exam_debt_details(db, bucket=b)

# --- Summary por sección dentro de un curso ---
@router.get("/summary_by_section")
@router.get("/summary_by_section/")
def exams_debt_summary_by_section(
    course_id: int = Query(..., description="ID del curso Moodle"),
    db: Session = Depends(get_db),
):
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id es requerido")
    return aq.get_exam_debt_summary_by_section(db, course_id=course_id)