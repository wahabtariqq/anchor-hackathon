"""Accounts, sessions and the identity dependency every router hangs off (docs/TDD-V2.md §4.3).

Replaces V1's app/identity.py. The V1 model was "a student id is a capability" — whoever held
the UUID could read and write that student. V2 puts a real account in front of it, but the
*shape* of what routers receive is deliberately unchanged: they still declare
`student: Student = Depends(current_student)` and still scope every query by `student.id`.
Only the import path moved, so no router body changes.

Passwords are bcrypt. Session tokens are opaque random strings; only their SHA-256 hash is
stored, so a database leak yields no usable session.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, Header, HTTPException
from sqlmodel import Session as DbSession
from sqlmodel import col, select

from app.config import settings
from app.db import get_session
from app.models import LoginFailure, Session as SessionRow, Student, User

TOKEN_BYTES = 32


# ---- passwords ----


def hash_password(password: str) -> str:
    """bcrypt refuses anything over 72 bytes rather than truncating; SignupRequest rejects it
    first with a 422, so reaching that error here means a caller bypassed validation."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(settings.BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # an over-long candidate or a corrupt stored hash is a failed login, never a 500
        return False


# ---- sessions ----


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session(db: DbSession, user: User) -> str:
    """Returns the raw token. It is never stored and cannot be recovered afterwards."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    db.add(
        SessionRow(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.SESSION_TTL_DAYS),
        )
    )
    db.commit()
    return token


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def _as_utc(moment: datetime) -> datetime:
    """SQLite hands back naive datetimes; Postgres hands back aware ones. Compare in UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


# ---- rate limiting ----


def recent_failures(db: DbSession, email: str) -> int:
    since = datetime.now(timezone.utc) - timedelta(minutes=settings.LOGIN_RATE_WINDOW_MIN)
    rows = db.exec(select(LoginFailure).where(col(LoginFailure.email) == email)).all()
    return sum(1 for row in rows if _as_utc(row.created_at) >= since)


def record_failure(db: DbSession, email: str) -> None:
    db.add(LoginFailure(email=email))
    db.commit()


# ---- dependencies ----


def current_user(
    authorization: str | None = Header(default=None),
    db: DbSession = Depends(get_session),
) -> User:
    token = bearer_token(authorization)
    if not token:
        raise HTTPException(401, "Missing or malformed Authorization header")
    row = db.exec(select(SessionRow).where(SessionRow.token_hash == hash_token(token))).first()
    if not row or _as_utc(row.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(401, "Invalid or expired session")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(401, "Invalid session")
    return user


def current_student(
    user: User = Depends(current_user),
    db: DbSession = Depends(get_session),
) -> Student:
    """The account's student profile — same return shape V1's header-based version had.

    404 rather than 401 on purpose: the caller is authenticated, they just have not finished
    onboarding, and the frontend routes 404 here to /onboarding (TDD-V2 §5.5).

    Newest first: re-onboarding creates a new Student rather than editing one (DECISIONS #8),
    so the most recent row is the live one.
    """
    student = db.exec(
        select(Student)
        .where(Student.user_id == user.id)
        .order_by(col(Student.created_at).desc(), col(Student.id))
    ).first()
    if not student:
        raise HTTPException(404, "No student profile yet — complete onboarding")
    return student
