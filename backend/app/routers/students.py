"""POST /api/students — create the student and their resolved course selections.

Always creates a new Student: re-onboarding never updates or deletes (DECISIONS #8).

V2: onboarding happens under an account, so the new row is attached to the caller
(TDD-V2 §4.2 — user_id "is only set once, either by onboarding-under-an-account or by
claim-on-signup"). Without this an account could never reach its own roadmap.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, select

from app.auth import current_user
from app.db import get_session
from app.models import Course, Student, StudentCourse, User
from app.schemas import StudentCreateRequest, StudentCreateResponse

router = APIRouter()


@router.post(
    "/api/students",
    response_model=StudentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_student(
    body: StudentCreateRequest,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> StudentCreateResponse:
    picked = [c.course_id for c in body.courses if c.course_id]
    catalog: dict[str, Course] = {}
    if picked:
        rows = session.exec(select(Course).where(col(Course.id).in_(picked))).all()
        catalog = {c.id: c for c in rows}
    unknown = [cid for cid in picked if cid not in catalog]
    if unknown:
        raise HTTPException(422, f"unknown course_id: {', '.join(unknown)}")

    student = Student(
        user_id=user.id,
        name=body.name,
        semester=body.semester,
        interests=list(body.interests),
    )
    session.add(student)

    custom_seen = 0
    for entry in body.courses:
        if entry.course_id:
            course = catalog[entry.course_id]
            code, name = course.code, course.name
            # curriculum_text resolves override > catalog default (CONTRACT.md §3)
            curriculum_text = (entry.curriculum_override or "").strip() or course.curriculum_text
        else:
            custom_seen += 1
            code = f"CUSTOM-{custom_seen}"
            name = (entry.custom_name or "").strip()          # non-empty per StudentCourseIn
            curriculum_text = (entry.curriculum_text or "").strip()
        session.add(
            StudentCourse(
                student_id=student.id,
                course_id=entry.course_id,
                code=code,
                name=name,
                curriculum_text=curriculum_text,
                semester_tag=entry.semester_tag,
            )
        )

    session.commit()
    return StudentCreateResponse(student_id=student.id)
