"""POST /api/analyze — the one model call, then persistence (docs/TDD.md §4.8).

Thin on purpose: 409/422 checks, hand off to the AI lane, persist, return. Every decision
about prompts, retries, truncation and DEMO_MODE lives in app/analysis/, which this module
imports and never edits.
"""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.identity import current_student
from app.models import Analysis, Student, StudentCourse
from app.persistence import persist_analysis
from app.schemas import OkResponse

router = APIRouter()
log = logging.getLogger(__name__)

# The AI lane's public surface, per integration seam 1: run(student, courses) -> (parsed, raw).
# TDD §4.8 names it `run`, the root CLAUDE.md names it `run_analysis`; accept either. Resolved
# at call time, not import time, so an app/analysis/ that is still being written cannot make
# this module - and therefore main.py - unimportable.
_ENTRY_POINTS = ("run", "run_analysis")


def _resolve_run() -> Callable[..., tuple[Any, str]]:
    try:
        import app.analysis as analysis
    except ImportError as e:
        log.warning("app.analysis is not importable: %s", e)
        raise HTTPException(503, "Analysis pipeline not available yet") from e

    for name in _ENTRY_POINTS:
        entry = getattr(analysis, name, None)
        if callable(entry):
            return entry
    log.warning("app.analysis exports none of %s yet", _ENTRY_POINTS)
    raise HTTPException(503, "Analysis pipeline not available yet")


@router.post("/api/analyze", response_model=OkResponse)
def analyze(
    student: Student = Depends(current_student),
    session: Session = Depends(get_session),
) -> OkResponse:
    if session.exec(select(Analysis).where(Analysis.student_id == student.id)).first():
        raise HTTPException(409, "Analysis already exists")
    courses = session.exec(
        select(StudentCourse).where(StudentCourse.student_id == student.id)
    ).all()
    if not courses:
        raise HTTPException(422, "Student has no courses")

    run = _resolve_run()
    try:
        parsed, raw = run(student, courses)
    except HTTPException:
        raise
    except Exception as e:                    # AnalysisFailed, or anything else the lane raises
        log.warning("analysis failed for student %s: %s", student.id, e)
        raise HTTPException(502, str(e) or "Analysis failed") from e

    persist_analysis(session, student.id, parsed, raw, list(courses))
    return OkResponse()
