"""The whole authorization story: a student id is a capability (docs/TDD.md §4.3).

Every router except courses.py depends on current_student and scopes its queries by
student.id. There is no ownership check anywhere else, by construction.
"""

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models import Student


def current_student(
    x_student_id: str = Header(alias="X-Student-Id"),
    session: Session = Depends(get_session),
) -> Student:
    student = session.get(Student, x_student_id)
    if not student:
        raise HTTPException(404, "Unknown student — start over")
    return student
