"""The REAL AI lane driven through Salman's routers — no stubs on this path.

`test_project_review.py` monkeypatches `generate_project` and `review_repo` onto the package
with `raising=False`, so it stays green whether this lane is written or not. That is the right
call for his lane, and it means green there is **not** evidence that the real implementation
fits his callers (HANDOFF §5, gotcha 8).

This file closes that gap. The model is still faked — at the `LLMClient` seam, so no test makes
a live call — but everything between the router and that seam is real: the actual prompt build,
the actual `ProjectOut` / `ReviewOut` validation, the actual cross-checks, the actual slug->id
resolution, and the actual `model_dump()` that `submit.py` stores.

The three things this catches that nothing else does: a return *shape* mismatch (a tuple where
he unpacks one value), a field name the routers read that the models do not have, and a payload
that validates in isolation but 502s once his slug resolution runs.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app.analysis as analysis_pkg
import app.routers.submit as submit_module
from app.analysis.project import generate_project
from app.analysis.review import review_repo
from app.github import RepoBundle
from app.models import Project, Submission
from tests.conftest import create_student, persist_demo_analysis


class OneShotClient:
    """An LLMClient that returns one scripted payload. The seam, and nothing above it, is fake."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.prompts: list[str] = []

    def complete_json(self, prompt, schema, *, max_tokens, temperature):
        self.prompts.append(prompt)
        return json.dumps(self.payload), "stop"


BUNDLE = RepoBundle(
    owner="ayesha",
    repo="log-pipeline",
    default_branch="main",
    tree=["README.md", "ingest.py", "store.py"],
    files={"README.md": "# Log pipeline\n\nIngestion and storage are separate modules."},
)


@pytest.fixture
def real_lane(monkeypatch: pytest.MonkeyPatch):
    """Install the real entry points, each backed by a scripted client."""
    seen: dict[str, Any] = {"prompts": [], "skills": None}

    def real_generate_project(title: str, one_liner: str, skills: list[Any]):
        seen["skills"] = skills
        client = OneShotClient(
            {
                "title": "Build a log-ingestion pipeline with replay",
                "spec": "Ingest, normalise and store log lines. Done when a query returns errors.",
                "criteria": [
                    "Ingestion and storage are separate modules with a defined interface.",
                    "The README documents the replay procedure.",
                    "Malformed lines are handled explicitly rather than crashing the run.",
                ],
                # drawn from the skills the ROUTER actually passed, so the cross-check and his
                # slug resolution both run against real data
                "verifies": [s.slug for s in skills][:2],
            }
        )
        out = generate_project(title, one_liner, skills, client=client)
        seen["prompts"].extend(client.prompts)
        return out

    def real_review_repo(project: Any, bundle: Any):
        client = OneShotClient(
            {
                "criteria_scores": [
                    {"criterion": c, "score": 2, "note": f"evidence for: {c[:30]}"}
                    for c in project.criteria
                ],
                "feedback": "Clear module boundaries; document the replay path next.",
            }
        )
        out = review_repo(project, bundle, client=client)
        seen["prompts"].extend(client.prompts)
        return out

    monkeypatch.setattr(analysis_pkg, "generate_project", real_generate_project, raising=False)
    monkeypatch.setattr(analysis_pkg, "review_repo", real_review_repo, raising=False)
    monkeypatch.setattr(submit_module, "fetch_repo", lambda url: BUNDLE)
    return seen


def a_role(client: TestClient, student_id: str) -> dict[str, Any]:
    return client.get("/api/roadmap", headers={"X-Student-Id": student_id}).json()["roles"][0]


def test_get_project_writes_a_row_from_a_real_ProjectOut(
    client: TestClient, session: Session, real_lane: dict[str, Any]
) -> None:
    """The shape check: `routers/project.py` does `out, _raw = generate_project(...)` and then
    reads `.title` / `.spec` / `.criteria` / `.verifies` off a real model."""
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    role = a_role(client, student_id)

    res = client.get(f"/api/project?role_id={role['id']}", headers={"X-Student-Id": student_id})
    assert res.status_code == 200, res.text

    payload = res.json()
    assert set(payload) == {"id", "role_id", "title", "spec", "criteria", "verifies"}
    assert len(payload["criteria"]) == 3
    # The slugs came back as DB ids, which only happens if his resolution found every one.
    role_skill_ids = {rs["skill_id"] for rs in role["skills"]}
    assert set(payload["verifies"]) <= role_skill_ids
    assert len(session.exec(select(Project)).all()) == 1


def test_the_real_prompt_gets_the_states_the_router_computed(
    client: TestClient, session: Session, real_lane: dict[str, Any]
) -> None:
    """`SkillState` crosses the lane boundary here: his dataclass into my renderer."""
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    role = a_role(client, student_id)
    client.get(f"/api/project?role_id={role['id']}", headers={"X-Student-Id": student_id})

    states = real_lane["skills"]
    assert states, "the router passed no skills"
    prompt = real_lane["prompts"][0]
    for state in states:
        assert f"{state.slug} — {state.name} — {state.weight} — {state.state}" in prompt


def test_a_full_submit_round_trip_stores_a_real_review(
    client: TestClient, session: Session, real_lane: dict[str, Any]
) -> None:
    """The other shape check: `submit.py` unpacks four values, calls `review.model_dump()`, and
    splats the result into `ReviewResponse(**stored, ...)`. A renamed field fails right here."""
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    role = a_role(client, student_id)
    project = client.get(f"/api/project?role_id={role['id']}", headers=headers).json()

    res = client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/r"},
        headers=headers,
    )
    assert res.status_code == 200, res.text

    review = res.json()["review"]
    assert (review["total"], review["max_total"], review["passed"]) == (6, 6, True)
    assert [c["criterion"] for c in review["criteria_scores"]] == project["criteria"]
    assert sorted(res.json()["verified_skill_ids"]) == sorted(project["verifies"])

    rows = session.exec(select(Submission)).all()
    assert len(rows) == 1
    assert set(rows[0].review) == {"criteria_scores", "feedback"}


def test_the_review_prompt_carries_the_stored_projects_criteria(
    client: TestClient, session: Session, real_lane: dict[str, Any]
) -> None:
    """The criteria make a full round trip -- generated, stored as a row, read back by
    `_project_out`, rendered into the review prompt -- and the echo check compares against the
    strings that survived all of it."""
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    role = a_role(client, student_id)
    project = client.get(f"/api/project?role_id={role['id']}", headers=headers).json()
    client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/r"},
        headers=headers,
    )

    review_prompt = real_lane["prompts"][-1]
    for i, criterion in enumerate(project["criteria"], 1):
        assert f"{i}. {criterion}" in review_prompt
    assert "README.md" in review_prompt
