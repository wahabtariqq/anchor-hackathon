"""GET /api/projects — every generated project with its full submission history.

The one net-new backend surface the Projects screen needs (docs/PRD-V2.md §4.6). `GET
/api/project?role_id=` still exists and is unaffected: it generates lazily for one role, this
one only reads what already exists across every role. Nothing here calls the model.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, desc, select

from app.auth import current_student
from app.db import get_session
from app.models import Project, Student, Submission
from app.routers.roadmap import project_response
from app.schemas import ProjectsResponse, ProjectWithHistory, SubmissionOut

router = APIRouter()


def submission_out(row: Submission) -> SubmissionOut:
    """The stored ReviewOut's two narrative fields, plus the three numbers scoring computed at
    submit time. `review` is the JSON column written by POST /api/submit."""
    return SubmissionOut(
        id=row.id,
        repo_url=row.repo_url,
        total=row.total,
        max_total=row.max_total,
        passed=row.passed,
        created_at=row.created_at,
        criteria_scores=(row.review or {}).get("criteria_scores", []),
        feedback=(row.review or {}).get("feedback", ""),
    )


@router.get("/api/projects", response_model=ProjectsResponse)
def list_projects(
    student: Student = Depends(current_student),
    session: Session = Depends(get_session),
) -> ProjectsResponse:
    projects = session.exec(select(Project).where(Project.student_id == student.id)).all()
    if not projects:
        return ProjectsResponse(projects=[])

    # one query for every submission, grouped in Python — a per-project query would be N+1 for
    # a screen that renders all of them at once
    history: dict[str, list[SubmissionOut]] = defaultdict(list)
    for row in session.exec(
        select(Submission)
        .where(col(Submission.project_id).in_([p.id for p in projects]))
        .order_by(desc(col(Submission.created_at)), desc(col(Submission.id)))
    ).all():
        history[row.project_id].append(submission_out(row))

    return ProjectsResponse(
        projects=[
            ProjectWithHistory(
                project=project_response(p),
                submissions=history.get(p.id, []),      # newest first
            )
            # newest project first: the role a student most recently opened Prove It on is the
            # one they came to this screen for
            for p in sorted(projects, key=lambda p: (p.created_at, p.id), reverse=True)
        ]
    )
