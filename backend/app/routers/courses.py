"""GET /api/courses — the catalog for the Setup screen. The only public route."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import Course
from app.schemas import CatalogCourseOut, CoursesResponse

router = APIRouter()


@router.get("/api/courses", response_model=CoursesResponse)
def list_courses(session: Session = Depends(get_session)) -> CoursesResponse:
    courses = session.exec(select(Course).order_by(Course.id)).all()
    return CoursesResponse(courses=[CatalogCourseOut.model_validate(c, from_attributes=True) for c in courses])
