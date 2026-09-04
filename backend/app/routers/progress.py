"""POST /api/progress — the only write after an analysis exists (docs/TDD.md §4.11).

Returns {"ok": true} and nothing else. Deliberately no recomputed fit: the client already
has it, and a fat response would tempt someone into refetching and killing the re-sort
animation, which is the whole demo.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.auth import current_student
from app.models import Analysis, Progress, Skill, Student
from app.schemas import OkResponse, ProgressRequest

router = APIRouter()


@router.post("/api/progress", response_model=OkResponse)
def set_progress(
    body: ProgressRequest,
    student: Student = Depends(current_student),
    session: Session = Depends(get_session),
) -> OkResponse:
    owns_skill = session.exec(
        select(Skill.id)
        .join(Analysis, Analysis.id == Skill.analysis_id)      # type: ignore[arg-type]
        .where(Skill.id == body.skill_id, Analysis.student_id == student.id)
    ).first()
    if not owns_skill:
        raise HTTPException(404, "Unknown skill")

    row = session.get(Progress, (student.id, body.skill_id))
    if body.checked and row is None:
        session.add(Progress(student_id=student.id, skill_id=body.skill_id))
    elif not body.checked and row is not None:
        session.delete(row)
    session.commit()
    return OkResponse()
