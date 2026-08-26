"""The whole authorization story: a student id is a capability (docs/TDD.md §4.3).

Every router except courses.py depends on current_student and scopes its queries by
student.id. There is no ownership check anywhere else, by construction.
"""

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models import Student


def current_student(
    x_student_id: str | None = Header(default=None, alias="X-Student-Id"),
    session: Session = Depends(get_session),
) -> Student:
    # TDD §11 treats missing and unknown alike: 404, so the client clears the stored id
    # and redirects to /setup. lib/api.ts omits the header entirely when localStorage is
    # empty, which is exactly the "cleared id, stale tab" case.
    student = session.get(Student, x_student_id) if x_student_id else None
    if not student:
        raise HTTPException(404, "Unknown student — start over")
    return student
