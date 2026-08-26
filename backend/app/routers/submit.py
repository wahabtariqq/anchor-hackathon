"""POST /api/submit — fetch the repo, review it, record the submission.

The only place `verified` can ever become true. Submissions are append-only: a failed attempt
is kept, and a later pass adds to the verified set without erasing anything.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.github import RepoError, fetch_repo
from app.identity import current_student
from app.models import Project, Skill, Student, Submission
from app.persistence import verified_skill_ids
from app.schemas import ReviewResponse, SubmitRequest, SubmitResponse

router = APIRouter()
log = logging.getLogger(__name__)

DEMO_SLEEP_SECONDS = 4      # PRD §12.1: the demo path still has to feel like work


def _resolve(name: str) -> Callable[..., Any]:
    try:
        import app.analysis as analysis
    except ImportError as e:
        log.warning("app.analysis is not importable: %s", e)
        raise HTTPException(503, "Repo review not available yet") from e
    entry = getattr(analysis, name, None)
    if not callable(entry):
        log.warning("app.analysis does not export %s yet", name)
        raise HTTPException(503, "Repo review not available yet")
    return entry


def _optional(name: str) -> Callable[..., Any] | None:
    try:
        import app.analysis as analysis
    except ImportError:
        return None
    entry = getattr(analysis, name, None)
    return entry if callable(entry) else None


class _ProjectOut:
    """The stored row in the shape app.analysis.review_repo expects — `verifies` back as
    slugs, since ProjectOut speaks slugs and the DB speaks ids (CONTRACT.md §1b)."""

    def __init__(self, row: Project, verifies: list[str]) -> None:
        self.title = row.title
        self.spec = row.spec
        self.criteria = list(row.criteria)
        self.verifies = verifies


def _project_out(session: Session, row: Project) -> _ProjectOut:
    ids = list(row.verifies or [])
    slugs = [s.slug for s in (session.get(Skill, sid) for sid in ids) if s]
    return _ProjectOut(row, slugs)


def _is_demo_submission(student: Student, repo_url: str) -> bool:
    if not (settings.DEMO_MODE and settings.DEMO_REPO_URL):
        return False
    if student.name.strip().lower() != settings.DEMO_STUDENT_NAME.strip().lower():
        return False
    return repo_url.strip().rstrip("/") == settings.DEMO_REPO_URL.strip().rstrip("/")


@router.post("/api/submit", response_model=SubmitResponse)
def submit(
    body: SubmitRequest,
    student: Student = Depends(current_student),
    session: Session = Depends(get_session),
) -> SubmitResponse:
    project = session.exec(
        select(Project).where(Project.student_id == student.id, Project.role_id == body.role_id)
    ).first()
    if not project:
        raise HTTPException(409, "Open the project first")

    load_demo = _optional("load_demo_review") if _is_demo_submission(student, body.repo_url) else None
    if load_demo:
        time.sleep(DEMO_SLEEP_SECONDS)
        review, total, max_total, passed = load_demo(_project_out(session, project))
    else:
        try:
            bundle = fetch_repo(body.repo_url)
        except RepoError as e:
            raise HTTPException(422, e.user_message) from e

        review_repo = _resolve("review_repo")
        try:
            review, total, max_total, passed = review_repo(_project_out(session, project), bundle)
        except HTTPException:
            raise
        except Exception as e:
            log.warning("review failed for %s: %s", body.repo_url, e)
            raise HTTPException(502, str(e) or "Repo review failed") from e

    stored = review.model_dump() if hasattr(review, "model_dump") else dict(review)

    session.add(
        Submission(
            student_id=student.id,
            role_id=project.role_id,
            project_id=project.id,
            repo_url=body.repo_url,
            review=stored,
            total=total,
            max_total=max_total,
            passed=passed,
            # frozen at submit time: a later edit to the project must not retro-verify skills
            verified_skill_ids=list(project.verifies) if passed else [],
        )
    )
    session.commit()

    return SubmitResponse(
        review=ReviewResponse(**stored, total=total, max_total=max_total, passed=passed),
        # the WHOLE set, so the client replaces verifiedIds rather than merging (CONTRACT.md §3)
        verified_skill_ids=sorted(verified_skill_ids(session, student.id)),
    )
