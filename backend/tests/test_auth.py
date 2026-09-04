"""Accounts, sessions, claim-on-signup and the rate limit (docs/TDD-V2.md §4.3-§4.4, §5.1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import hash_token
from app.config import settings
from app.models import LoginFailure, Session as SessionRow, Student, User
from tests.conftest import DEMO_STUDENT, create_account

GOOD = {"email": "ayesha@example.com", "password": "hunter2-strong", "name": "Ayesha"}


def signup(client: TestClient, **overrides: object):
    return client.post("/api/auth/signup", json={**GOOD, **overrides})


def login(client: TestClient, **overrides: object):
    body = {"email": GOOD["email"], "password": GOOD["password"]}
    return client.post("/api/auth/login", json={**body, **overrides})


# ---- signup ----


def test_signup_creates_an_account_and_returns_no_token(client: TestClient) -> None:
    res = signup(client)
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body) == {"user"}, "signup must not establish a session (DECISIONS #78)"
    assert set(body["user"]) == {"id", "email", "name", "created_at"}
    assert body["user"]["email"] == "ayesha@example.com"


def test_signup_never_returns_the_password_or_its_hash(client: TestClient) -> None:
    body = signup(client).text
    assert GOOD["password"] not in body
    assert "hash" not in body.lower()


def test_the_password_is_stored_hashed_not_in_the_clear(client: TestClient, session: Session) -> None:
    signup(client)
    user = session.exec(select(User)).one()
    assert user.password_hash != GOOD["password"]
    assert user.password_hash.startswith("$2")          # a bcrypt digest, not a plaintext copy


def test_email_is_lowercased_and_unique(client: TestClient) -> None:
    assert signup(client, email="Ayesha@Example.COM").json()["user"]["email"] == "ayesha@example.com"
    clash = signup(client, email="  AYESHA@example.com  ")
    assert clash.status_code == 409
    assert clash.json()["detail"] == "Email already registered"


@pytest.mark.parametrize(
    ("field", "value"),
    [("password", "short"), ("password", "x" * 73), ("email", "nope"), ("email", "a@b"), ("name", "   ")],
    ids=["short password", "73-byte password", "no @", "no tld", "blank name"],
)
def test_signup_validation(client: TestClient, field: str, value: str) -> None:
    assert signup(client, **{field: value}).status_code == 422


def test_a_72_byte_password_is_accepted_not_truncated(client: TestClient) -> None:
    """bcrypt's exact limit. One byte over is a 422; at the limit it must round-trip whole."""
    password = "p" * 72
    assert signup(client, password=password).status_code == 200
    assert login(client, password=password).status_code == 200
    assert login(client, password="p" * 71).status_code == 401


# ---- login ----


def test_login_issues_a_token_that_works(client: TestClient) -> None:
    signup(client)
    res = login(client)
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["email"] == "ayesha@example.com"
    headers = {"Authorization": f"Bearer {body['token']}"}
    # authenticated, but not onboarded yet
    assert client.get("/api/roadmap", headers=headers).status_code == 404


def test_only_the_token_hash_is_stored(client: TestClient, session: Session) -> None:
    signup(client)
    token = login(client).json()["token"]
    row = session.exec(select(SessionRow)).one()
    assert row.token_hash == hash_token(token)
    assert token not in row.token_hash, "the raw token must never be recoverable from the row"


@pytest.mark.parametrize(
    ("email", "password"),
    [("ayesha@example.com", "wrong-password"), ("nobody@example.com", "hunter2-strong")],
    ids=["wrong password", "unknown email"],
)
def test_login_gives_the_same_answer_for_both_failures(
    client: TestClient, email: str, password: str
) -> None:
    """Different messages here would be an account-enumeration oracle."""
    signup(client)
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 401
    assert res.json()["detail"] == "Wrong email or password"


def test_login_bumps_last_seen_at_but_ordinary_requests_do_not(
    client: TestClient, session: Session
) -> None:
    """last_seen_at is the dashboard delta's baseline — it must not creep forward mid-session."""
    signup(client)
    token = login(client).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    session.expire_all()
    after_login = session.exec(select(User)).one().last_seen_at

    client.get("/api/roadmap", headers=headers)
    client.get("/api/courses")
    session.expire_all()
    assert session.exec(select(User)).one().last_seen_at == after_login

    login(client)
    session.expire_all()
    assert session.exec(select(User)).one().last_seen_at > after_login


# ---- rate limit ----


def test_login_rate_limit_trips_and_is_per_email(client: TestClient) -> None:
    signup(client)
    for _ in range(settings.LOGIN_RATE_LIMIT):
        assert login(client, password="wrong-password").status_code == 401

    limited = login(client)                       # the CORRECT password, still refused
    assert limited.status_code == 429
    assert "Too many attempts" in limited.json()["detail"]

    signup(client, email="other@example.com")
    assert client.post(
        "/api/auth/login", json={"email": "other@example.com", "password": GOOD["password"]}
    ).status_code == 200, "the limit must be per email, not global"


def test_failures_outside_the_window_do_not_count(client: TestClient, session: Session) -> None:
    signup(client)
    stale = datetime.now(timezone.utc) - timedelta(minutes=settings.LOGIN_RATE_WINDOW_MIN + 1)
    for _ in range(settings.LOGIN_RATE_LIMIT + 5):
        session.add(LoginFailure(email=GOOD["email"], created_at=stale))
    session.commit()
    assert login(client).status_code == 200


# ---- logout ----


def test_logout_kills_only_that_session(client: TestClient) -> None:
    signup(client)
    first = login(client).json()["token"]
    second = login(client).json()["token"]
    one, two = ({"Authorization": f"Bearer {t}"} for t in (first, second))

    assert client.post("/api/auth/logout", headers=one).json() == {"ok": True}
    assert client.get("/api/roadmap", headers=one).status_code == 401
    assert client.get("/api/roadmap", headers=two).status_code == 404      # still signed in


def test_logout_is_idempotent_and_tolerates_a_stale_token(client: TestClient) -> None:
    signup(client)
    headers = {"Authorization": f"Bearer {login(client).json()['token']}"}
    for _ in range(2):
        assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers={"Authorization": "Bearer nope"}).status_code == 200
    assert client.post("/api/auth/logout").status_code == 200


def test_logout_all_kills_every_session(client: TestClient, session: Session) -> None:
    signup(client)
    tokens = [login(client).json()["token"] for _ in range(3)]
    headers = [{"Authorization": f"Bearer {t}"} for t in tokens]

    assert client.post("/api/auth/logout_all", headers=headers[0]).status_code == 200
    for h in headers:
        assert client.get("/api/roadmap", headers=h).status_code == 401
    assert session.exec(select(SessionRow)).all() == []


def test_logout_all_needs_a_valid_session(client: TestClient) -> None:
    assert client.post("/api/auth/logout_all").status_code == 401


def test_one_users_logout_all_leaves_another_user_alone(client: TestClient) -> None:
    _, mine = create_account(client)
    _, theirs = create_account(client)
    assert client.post("/api/auth/logout_all", headers=mine).status_code == 200
    assert client.get("/api/roadmap", headers=theirs).status_code == 404      # still authenticated


# ---- claim-on-signup ----


def test_claim_on_signup_adopts_an_unclaimed_student(client: TestClient, session: Session) -> None:
    orphan = Student(name="Ayesha", semester=4, interests=["Databases", "Security"])
    session.add(orphan)
    session.commit()
    orphan_id = orphan.id

    signup(client, claim_student_id=orphan_id)
    session.expire_all()
    user = session.exec(select(User)).one()
    assert session.get(Student, orphan_id).user_id == user.id

    headers = {"Authorization": f"Bearer {login(client).json()['token']}"}
    # the claimed student is now reachable through the account
    assert client.post("/api/analyze", headers=headers).status_code == 422    # no courses, but found


def test_claim_never_steals_a_student_that_already_has_an_owner(
    client: TestClient, session: Session
) -> None:
    first_student = create_account_with_student(client)
    thief = signup(client, email="thief@example.com", claim_student_id=first_student)
    assert thief.status_code == 200, "the signup itself still succeeds"

    session.expire_all()
    owner_email = session.exec(
        select(User).where(User.id == session.get(Student, first_student).user_id)
    ).one().email
    assert owner_email != "thief@example.com"


def test_claiming_an_unknown_id_is_not_an_error(client: TestClient) -> None:
    assert signup(client, claim_student_id="no-such-student").status_code == 200


def create_account_with_student(client: TestClient) -> str:
    _, headers = create_account(client)
    res = client.post("/api/students", json=DEMO_STUDENT, headers=headers)
    assert res.status_code == 201
    return res.json()["student_id"]


# ---- account scoping ----


def test_a_student_is_reachable_only_through_its_own_account(client: TestClient) -> None:
    mine = create_account_with_student(client)
    _, other = create_account(client)
    assert client.get("/api/roadmap", headers=other).status_code == 404, (
        "another account must not see this student's roadmap"
    )
    assert mine


def test_onboarding_attaches_the_student_to_the_caller(client: TestClient, session: Session) -> None:
    _, headers = create_account(client)
    student_id = client.post("/api/students", json=DEMO_STUDENT, headers=headers).json()["student_id"]
    user = session.exec(select(User)).one()
    assert session.get(Student, student_id).user_id == user.id


def test_the_newest_student_wins_when_an_account_re_onboards(
    client: TestClient, session: Session
) -> None:
    """Re-onboarding creates a new Student rather than editing one (DECISIONS #8)."""
    _, headers = create_account(client)
    first = client.post("/api/students", json=DEMO_STUDENT, headers=headers).json()["student_id"]
    second = client.post(
        "/api/students", json={**DEMO_STUDENT, "semester": 7}, headers=headers
    ).json()["student_id"]
    assert first != second

    from app.auth import current_student
    from app.models import User as U

    user = session.exec(select(U)).one()
    assert current_student(user=user, db=session).id == second
