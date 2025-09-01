# app/api/routers/courses.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_moodle_db
from app.crud import course_queries

router = APIRouter()

@router.get("/courses/rankings")
def get_course_rankings_api(moodle_db: Session = Depends(get_moodle_db)):
    """Endpoint para obtener los rankings de cursos."""
    return course_queries.get_course_rankings(moodle_db)