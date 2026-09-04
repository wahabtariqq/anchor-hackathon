"""POST /api/auth/signup · /login · /logout · /logout_all (docs/TDD-V2.md §4.4).

The only two routes in the API that do not require a bearer token.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, col, delete, select

from app.auth import (
    bearer_token,
    current_user,
    hash_password,
    hash_token,
    issue_session,
    record_failure,
    recent_failures,
    verify_password,
)
from app.config import settings
from app.db import get_session
from app.models import Session as SessionRow
from app.models import Student, User
from app.schemas import AuthResponse, LoginRequest, OkResponse, SignupRequest, SignupResponse, UserOut

router = APIRouter(prefix="/api/auth")
log = logging.getLogger(__name__)


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, created_at=user.created_at)


@router.post("/signup", response_model=SignupResponse)
def signup(body: SignupRequest, db: Session = Depends(get_session)) -> SignupResponse:
    if db.exec(select(User).where(User.email == body.email)).first():
        raise HTTPException(409, "Email already registered")

    user = User(email=body.email, password_hash=hash_password(body.password), name=body.name)
    db.add(user)
    db.commit()

    # Claim-on-signup (TDD-V2 §5.1): adopt the caller's V1 anonymous student, but never steal
    # one that already belongs to somebody. Silent on refusal — the id came from the client.
    if body.claim_student_id:
        student = db.get(Student, body.claim_student_id)
        if student and student.user_id is None:
            student.user_id = user.id
            db.add(student)
            db.commit()
        else:
            log.info("signup: declined to claim student %s", body.claim_student_id)

    # No session here. Signup creates the account; a login establishes the session, signup
    # included (DECISIONS #78) — the client sends the student to /login next.
    return SignupResponse(user=_user_out(user))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_session)) -> AuthResponse:
    if recent_failures(db, body.email) >= settings.LOGIN_RATE_LIMIT:
        raise HTTPException(429, "Too many attempts — try again later")

    user = db.exec(select(User).where(User.email == body.email)).first()
    if not user or not verify_password(body.password, user.password_hash):
        record_failure(db, body.email)
        # Never say which was wrong: it would turn this into an account-enumeration oracle.
        raise HTTPException(401, "Wrong email or password")

    # Bumped only here — it is the dashboard delta's baseline and must hold still for the
    # whole session rather than creeping forward as the student uses the app (TDD-V2 §4.4).
    token = issue_session(db, user)
    user.last_seen_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    return AuthResponse(token=token, user=_user_out(user))


@router.post("/logout", response_model=OkResponse)
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_session),
) -> OkResponse:
    """Idempotent by design: logging out twice, or with a stale token, is still a success —
    the client's goal (no usable session) is met either way."""
    token = bearer_token(authorization)
    if token:
        db.exec(delete(SessionRow).where(col(SessionRow.token_hash) == hash_token(token)))
        db.commit()
    return OkResponse()


@router.post("/logout_all", response_model=OkResponse)
def logout_all(
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> OkResponse:
    db.exec(delete(SessionRow).where(col(SessionRow.user_id) == user.id))
    db.commit()
    return OkResponse()
