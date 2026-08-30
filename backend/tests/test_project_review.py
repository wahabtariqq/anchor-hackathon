"""Prove It: app/github.py, GET /api/project, POST /api/submit.

The AI lane is stubbed by setting attributes on the (still empty) app.analysis module — the
same late lookup the routers do at call time. github.py is driven through httpx.MockTransport,
so nothing here touches the network.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app.analysis as analysis_pkg
import app.routers.submit as submit_module
from app.config import settings
from app.github import MAX_FILE_BYTES, MAX_TOTAL_BYTES, RepoError, fetch_repo, parse_github_url
from app.models import Project, Role, Submission
from tests.conftest import create_student, persist_demo_analysis

# --------------------------------------------------------------------------- github.py


def gh_transport(
    *,
    tree: list[dict[str, str]] | None = None,
    branch: str = "main",
    raw: bytes = b"# readme",
) -> httpx.MockTransport:
    tree = tree if tree is not None else [{"path": "README.md", "type": "blob"}]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/git/trees/" in url:
            return httpx.Response(200, json={"tree": tree})
        if url.startswith("https://api.github.com/repos/"):
            return httpx.Response(200, json={"default_branch": branch})
        return httpx.Response(200, content=raw)

    return httpx.MockTransport(handler)


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/",
        "https://github.com/owner/repo.git",
        "http://github.com/owner/repo",
        "https://www.github.com/owner/repo",
        "https://github.com/owner/repo/tree/main",
        "https://github.com/owner/repo/blob/main/src/x.py",
        "  https://github.com/owner/repo  ",
    ],
)
def test_parse_accepts_the_urls_people_paste(url: str) -> None:
    assert parse_github_url(url) == ("owner", "repo")


@pytest.mark.parametrize(
    "url",
    [
        "", "not a url", "https://gitlab.com/o/r", "https://github.com/owner", "https://github.com/",
        "ftp://github.com/o/r", "https://evilgithub.com/o/r", "https://github.com.evil.com/o/r",
    ],
)
def test_parse_rejects_everything_else(url: str) -> None:
    with pytest.raises(RepoError):
        parse_github_url(url)


def test_fetch_picks_readme_first_and_skips_noise() -> None:
    tree = [
        {"path": "src/deep/nested/thing.py", "type": "blob"},
        {"path": "README.md", "type": "blob"},
        {"path": "main.py", "type": "blob"},
        {"path": "node_modules/left-pad/index.js", "type": "blob"},
        {"path": "dist/bundle.js", "type": "blob"},
        {"path": "package-lock.json", "type": "blob"},
        {"path": "src", "type": "tree"},
    ]
    with httpx.Client(transport=gh_transport(tree=tree, branch="trunk")) as client:
        bundle = fetch_repo("https://github.com/o/r", client=client)

    assert bundle.default_branch == "trunk"
    assert list(bundle.files)[0] == "README.md"
    assert "main.py" in bundle.files                       # shallower than src/deep/nested
    assert not any(p.startswith(("node_modules/", "dist/")) for p in bundle.files)
    assert "package-lock.json" not in bundle.files
    assert "src" not in bundle.tree                        # trees are not blobs


def test_fetch_skips_binaries_and_caps_size() -> None:
    tree = [{"path": "README.md", "type": "blob"}, {"path": "logo.png", "type": "blob"}] + [
        {"path": f"m{i}.py", "type": "blob"} for i in range(8)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/git/trees/" in url:
            return httpx.Response(200, json={"tree": tree})
        if url.startswith("https://api.github.com/repos/"):
            return httpx.Response(200, json={"default_branch": "main"})
        if url.endswith("logo.png"):
            return httpx.Response(200, content=b"\x89PNG\x00\x00binary")
        return httpx.Response(200, content=b"x" * 30_000)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        bundle = fetch_repo("https://github.com/o/r", client=client)

    assert "logo.png" not in bundle.files
    assert all(len(body) <= MAX_FILE_BYTES + 20 for body in bundle.files.values())
    assert sum(len(body) for body in bundle.files.values()) <= MAX_TOTAL_BYTES
    assert any(body.endswith("…[truncated]") for body in bundle.files.values())


@pytest.mark.parametrize(
    ("status", "headers", "expected"),
    [
        (404, {}, "isn't public"),
        (403, {"x-ratelimit-remaining": "0"}, "rate-limiting"),
        (403, {"x-ratelimit-remaining": "4999"}, "isn't public"),
        (500, {}, "check the URL"),
    ],
)
def test_github_failures_become_user_facing_messages(
    status: int, headers: dict[str, str], expected: str
) -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(status, headers=headers, content=b"{}"))
    with httpx.Client(transport=transport) as client:
        with pytest.raises(RepoError) as caught:
            fetch_repo("https://github.com/o/r", client=client)
    assert expected in caught.value.user_message


def test_a_repo_with_nothing_readable_is_a_repo_error() -> None:
    tree = [{"path": "node_modules/x.js", "type": "blob"}]
    with httpx.Client(transport=gh_transport(tree=tree)) as client:
        with pytest.raises(RepoError, match="no files yet"):
            fetch_repo("https://github.com/o/r", client=client)


def test_a_network_failure_is_a_repo_error_not_a_500() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with httpx.Client(transport=httpx.MockTransport(boom)) as client:
        with pytest.raises(RepoError, match="Couldn't reach GitHub"):
            fetch_repo("https://github.com/o/r", client=client)


# --------------------------------------------------------------------- stubs for the AI lane


def fake_project(verifies: list[str] | None = None, criteria: list[str] | None = None) -> Any:
    return SimpleNamespace(
        title="Build a log-ingestion pipeline",
        spec="Ingest, transform and store log lines. Done when a query returns yesterday's errors.",
        criteria=criteria or ["Has a README", "Parses input", "Stores output"],
        verifies=verifies or [],
    )


def fake_review(scores: list[int], criteria: list[str]) -> Any:
    review = SimpleNamespace(
        criteria_scores=[
            {"criterion": c, "score": s, "note": "seen in the repo"}
            for c, s in zip(criteria, scores)
        ],
        feedback="Solid structure, thin on tests.",
    )
    review.model_dump = lambda: {                       # type: ignore[attr-defined]
        "criteria_scores": review.criteria_scores,
        "feedback": review.feedback,
    }
    total, max_total = sum(scores), 2 * len(criteria)
    passed = total >= math.ceil(settings.REVIEW_PASS_RATIO * max_total)
    return review, total, max_total, passed


@pytest.fixture
def ai_lane(monkeypatch: pytest.MonkeyPatch):
    """Install generate_project / review_repo on the empty app.analysis package."""

    state: dict[str, Any] = {"calls": 0, "verifies": [], "scores": [2, 2, 2], "states": None}

    def generate_project(title: str, one_liner: str, skills: list[Any]) -> tuple[Any, str]:
        state["calls"] += 1
        state["states"] = skills
        slugs = state["verifies"] or [s.slug for s in skills][:2]
        return fake_project(verifies=slugs), "{}"

    def review_repo(project: Any, bundle: Any) -> tuple[Any, int, int, bool]:
        return fake_review(state["scores"], project.criteria)

    monkeypatch.setattr(analysis_pkg, "generate_project", generate_project, raising=False)
    monkeypatch.setattr(analysis_pkg, "review_repo", review_repo, raising=False)
    monkeypatch.setattr(submit_module, "fetch_repo", lambda url: SimpleNamespace(files={}, tree=[]))
    return state


def a_role(client: TestClient, session: Session, student_id: str) -> dict[str, Any]:
    body = client.get("/api/roadmap", headers={"X-Student-Id": student_id}).json()
    return body["roles"][0]


# ------------------------------------------------------------------------- GET /api/project


def test_project_is_503_until_the_ai_lane_exists(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # app.analysis now really exports generate_project (S6), so the 503 branch has to be
    # provoked rather than inherited from the package being empty. Deleting the attribute is
    # what the router actually keys on -- and without this the test would make a LIVE model
    # call, which no test in this repo is allowed to do.
    monkeypatch.delattr(analysis_pkg, "generate_project", raising=False)
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    role = a_role(client, session, student_id)

    res = client.get(f"/api/project?role_id={role['id']}", headers={"X-Student-Id": student_id})
    assert res.status_code == 503
    assert res.json()["detail"] == "Project generation not available yet"


def test_project_404s_for_a_role_outside_this_students_analysis(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    mine, theirs = create_student(client), create_student(client)
    persist_demo_analysis(session, mine)
    persist_demo_analysis(session, theirs)
    their_role = a_role(client, session, theirs)

    res = client.get(f"/api/project?role_id={their_role['id']}", headers={"X-Student-Id": mine})
    assert res.status_code == 404
    res = client.get("/api/project?role_id=nope", headers={"X-Student-Id": mine})
    assert res.status_code == 404


def test_project_generates_once_then_serves_the_cached_row(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    role = a_role(client, session, student_id)
    headers = {"X-Student-Id": student_id}

    first = client.get(f"/api/project?role_id={role['id']}", headers=headers)
    assert first.status_code == 200, first.text
    second = client.get(f"/api/project?role_id={role['id']}", headers=headers)

    assert first.json() == second.json()
    assert ai_lane["calls"] == 1, "the second call must not hit the model"
    assert len(session.exec(select(Project)).all()) == 1

    payload = first.json()
    assert set(payload) == {"id", "role_id", "title", "spec", "criteria", "verifies"}
    role_skill_ids = {rs["skill_id"] for rs in role["skills"]}
    assert payload["verifies"], "the project must verify something"
    assert set(payload["verifies"]) <= role_skill_ids, "slugs must resolve to this role's skill ids"


def test_project_rejects_verifies_outside_the_role(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    ai_lane["verifies"] = ["not-a-skill-in-this-role"]
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    role = a_role(client, session, student_id)

    res = client.get(f"/api/project?role_id={role['id']}", headers={"X-Student-Id": student_id})
    assert res.status_code == 502
    assert session.exec(select(Project)).all() == [], "no row may be written for a bad project"


def test_skill_states_describe_what_the_student_already_has(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    body = client.get("/api/roadmap", headers=headers).json()
    depth = {s["id"]: s["coverage_depth"] for s in body["skills"]}
    # a role that actually has an uncovered skill, so there is something to tick
    role = max(
        body["roles"],
        key=lambda r: sum(1 for rs in r["skills"] if depth[rs["skill_id"]] is None),
    )
    ticked = next(rs["skill_id"] for rs in role["skills"] if depth[rs["skill_id"]] is None)
    client.post("/api/progress", json={"skill_id": ticked, "checked": True}, headers=headers)

    client.get(f"/api/project?role_id={role['id']}", headers=headers)
    states = {s.slug: s.state for s in ai_lane["states"]}
    slug_of = {s["id"]: s["slug"] for s in body["skills"]}

    assert states[slug_of[ticked]] == "ticked"
    for rs in role["skills"]:
        expected = {
            "full": "covered:full",
            "partial": "covered:partial",
            None: "ticked" if rs["skill_id"] == ticked else "missing",
        }[depth[rs["skill_id"]]]
        assert states[slug_of[rs["skill_id"]]] == expected


# -------------------------------------------------------------------------- POST /api/submit


def test_submit_409s_before_a_project_exists(client: TestClient, session: Session) -> None:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    role = a_role(client, session, student_id)

    res = client.post(
        "/api/submit",
        json={"role_id": role["id"], "repo_url": "https://github.com/o/r"},
        headers={"X-Student-Id": student_id},
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Open the project first"


def test_a_repo_error_is_a_422_with_the_students_message(
    client: TestClient, session: Session, ai_lane: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    role = a_role(client, session, student_id)
    headers = {"X-Student-Id": student_id}
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    def refuse(url: str) -> Any:
        raise RepoError("That repo isn't public or doesn't exist")

    monkeypatch.setattr(submit_module, "fetch_repo", refuse)
    res = client.post(
        "/api/submit", json={"role_id": role["id"], "repo_url": "https://github.com/o/r"}, headers=headers
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "That repo isn't public or doesn't exist"
    assert session.exec(select(Submission)).all() == [], "a failed fetch writes no submission"


def test_a_review_failure_is_a_502(
    client: TestClient, session: Session, ai_lane: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    role = a_role(client, session, student_id)
    headers = {"X-Student-Id": student_id}
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    def explode(project: Any, bundle: Any) -> Any:
        raise RuntimeError("review failed after 2 attempts")

    monkeypatch.setattr(analysis_pkg, "review_repo", explode, raising=False)
    res = client.post(
        "/api/submit", json={"role_id": role["id"], "repo_url": "https://github.com/o/r"}, headers=headers
    )
    assert res.status_code == 502
    assert session.exec(select(Submission)).all() == []


def test_a_passing_submission_verifies_skills_and_raises_fit(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    before = client.get("/api/roadmap", headers=headers).json()
    role = before["roles"][0]
    project = client.get(f"/api/project?role_id={role['id']}", headers=headers).json()

    res = client.post(
        "/api/submit", json={"role_id": role["id"], "repo_url": "https://github.com/o/r"}, headers=headers
    )
    assert res.status_code == 200, res.text
    payload = res.json()

    assert payload["review"]["passed"] is True
    assert payload["review"]["total"] == 6 and payload["review"]["max_total"] == 6
    assert [c["criterion"] for c in payload["review"]["criteria_scores"]] == project["criteria"]
    assert sorted(payload["verified_skill_ids"]) == sorted(project["verifies"])

    after = client.get("/api/roadmap", headers=headers).json()
    verified = {s["id"] for s in after["skills"] if s["verified"]}
    assert verified == set(project["verifies"])
    moved = next(r for r in after["roles"] if r["id"] == role["id"])
    assert moved["fit_percent"] >= role["fit_percent"], "proof must never lower a score"
    assert moved["project"] is not None and moved["latest_review"] is not None
    assert moved["latest_review"]["passed"] is True


def test_proof_on_an_uncovered_skill_raises_fit_across_every_role_that_needs_it(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    """The v4 mechanic: one repo, several cards move. Skills are shared, so proof propagates."""
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    before = client.get("/api/roadmap", headers=headers).json()
    depth = {s["id"]: s["coverage_depth"] for s in before["skills"]}

    # a role with real gaps, so the verified skills are ones coverage wasn't already paying for
    role = max(
        before["roles"],
        key=lambda r: sum(1 for rs in r["skills"] if depth[rs["skill_id"]] is None),
    )
    project = client.get(f"/api/project?role_id={role['id']}", headers=headers).json()
    assert any(depth[sid] is None for sid in project["verifies"]), "fixture should leave a gap"

    client.post(
        "/api/submit", json={"role_id": role["id"], "repo_url": "https://github.com/o/r"}, headers=headers
    )
    after = client.get("/api/roadmap", headers=headers).json()

    fit_before = {r["id"]: r["fit_percent"] for r in before["roles"]}
    risen = [r for r in after["roles"] if r["fit_percent"] > fit_before[r["id"]]]
    assert all(r["fit_percent"] >= fit_before[r["id"]] for r in after["roles"]), "nothing may fall"
    assert next(r for r in risen if r["id"] == role["id"]), "the submitted role must rise"
    assert len(risen) > 1, "a shared skill should move more than the one card"


def test_a_failing_submission_verifies_nothing_but_is_still_recorded(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    ai_lane["scores"] = [0, 1, 0]                     # 1 of 6, below the 0.6 ratio
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    role = a_role(client, session, student_id)
    client.get(f"/api/project?role_id={role['id']}", headers=headers)

    payload = client.post(
        "/api/submit", json={"role_id": role["id"], "repo_url": "https://github.com/o/r"}, headers=headers
    ).json()

    assert payload["review"]["passed"] is False
    assert payload["verified_skill_ids"] == []
    rows = session.exec(select(Submission)).all()
    assert len(rows) == 1 and rows[0].verified_skill_ids == []
    after = client.get("/api/roadmap", headers=headers).json()
    assert all(s["verified"] is False for s in after["skills"])
    assert next(r for r in after["roles"] if r["id"] == role["id"])["latest_review"]["passed"] is False


def test_verified_is_the_union_across_roles_and_attempts(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    body = client.get("/api/roadmap", headers=headers).json()
    first, second = body["roles"][0], body["roles"][1]

    p1 = client.get(f"/api/project?role_id={first['id']}", headers=headers).json()
    r1 = client.post(
        "/api/submit", json={"role_id": first["id"], "repo_url": "https://github.com/o/a"}, headers=headers
    ).json()
    p2 = client.get(f"/api/project?role_id={second['id']}", headers=headers).json()
    r2 = client.post(
        "/api/submit", json={"role_id": second["id"], "repo_url": "https://github.com/o/b"}, headers=headers
    ).json()

    assert set(r1["verified_skill_ids"]) == set(p1["verifies"])
    # the second response carries the WHOLE set, not just the second project's skills
    assert set(r2["verified_skill_ids"]) == set(p1["verifies"]) | set(p2["verifies"])

    after = client.get("/api/roadmap", headers=headers).json()
    assert {s["id"] for s in after["skills"] if s["verified"]} == set(r2["verified_skill_ids"])


def test_a_later_failure_never_unverifies_an_earlier_pass(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    role = a_role(client, session, student_id)
    project = client.get(f"/api/project?role_id={role['id']}", headers=headers).json()

    client.post("/api/submit", json={"role_id": role["id"], "repo_url": "https://github.com/o/a"}, headers=headers)
    ai_lane["scores"] = [0, 0, 0]
    payload = client.post(
        "/api/submit", json={"role_id": role["id"], "repo_url": "https://github.com/o/b"}, headers=headers
    ).json()

    assert payload["review"]["passed"] is False
    assert set(payload["verified_skill_ids"]) == set(project["verifies"]), "nothing lowers a score"
    after = client.get("/api/roadmap", headers=headers).json()
    assert {s["id"] for s in after["skills"] if s["verified"]} == set(project["verifies"])
    # latest_review is the newer, failing one — the badge tells the truth about the last attempt
    assert next(r for r in after["roles"] if r["id"] == role["id"])["latest_review"]["passed"] is False
    assert len(session.exec(select(Submission)).all()) == 2, "submissions are append-only"


def test_submit_requires_a_student(client: TestClient) -> None:
    res = client.post("/api/submit", json={"role_id": "x", "repo_url": "https://github.com/o/r"})
    assert res.status_code == 404


def test_the_pass_threshold_is_the_configured_ratio(
    client: TestClient, session: Session, ai_lane: dict[str, Any]
) -> None:
    # 4 of 6 = 0.667 >= 0.6 passes; 3 of 6 = 0.5 does not
    student_id = create_student(client)
    persist_demo_analysis(session, student_id)
    headers = {"X-Student-Id": student_id}
    roles = client.get("/api/roadmap", headers=headers).json()["roles"]

    ai_lane["scores"] = [2, 2, 0]
    client.get(f"/api/project?role_id={roles[0]['id']}", headers=headers)
    passed = client.post(
        "/api/submit", json={"role_id": roles[0]["id"], "repo_url": "https://github.com/o/a"}, headers=headers
    ).json()
    assert passed["review"]["total"] == 4 and passed["review"]["passed"] is True

    ai_lane["scores"] = [2, 1, 0]
    client.get(f"/api/project?role_id={roles[1]['id']}", headers=headers)
    failed = client.post(
        "/api/submit", json={"role_id": roles[1]["id"], "repo_url": "https://github.com/o/b"}, headers=headers
    ).json()
    assert failed["review"]["total"] == 3 and failed["review"]["passed"] is False
