# ANCHOR — Technical Design Document V2

**Implements:** `docs/PRD-V2.md`
**Stack:** unchanged — FastAPI + SQLModel + Postgres/SQLite · React + Vite + Tailwind + shadcn/ui. No new AI stack; `backend/app/analysis/` is frozen (PRD-V2 §2 non-goals).
**Audience:** the same three engineers who built V1 — Salman, Umer, Wahab
**Status:** Design proposed, not yet locked. Mirrors `docs/TDD.md`'s section shape so the two documents read side by side.
**Lane status (2026-09-04): all three lanes are done.** Wahab's frontend shipped first,
fixture-backed (§7.5). Salman's auth lane followed (`user`/`session`/`login_failure`,
`/api/auth/*`, the `current_student` swap). Umer's events/aggregation lane landed last —
`event`/`fit_snapshot`, `app/events.py`, the `/progress` and `/submit` transactional writes, and
`/api/dashboard`, `/api/skills`, `/api/projects` — and the frontend was cut over to it: the
fixture shim for those three endpoints and `lib/eventLog.ts` are **deleted**, exactly as §7.5
said they would be. `VITE_USE_FIXTURE` survives as an offline/demo convenience only.

*V2 adds: real accounts (`user`, `session`), an append-only `event` log, `fit_snapshot` history,
~~four~~ three new screens (Dashboard, Skills, Projects — a fourth, Profile, was built then removed,
DECISIONS #85) plus Login/Signup behind an app shell, and a design-token pass. It does **not** touch
`backend/app/analysis/`, the three model calls, the fit formula, or the roadmap response shape —
those are frozen exactly as TDD v4 left them.*

---

## 1. Scope

This document specifies *how* `docs/PRD-V2.md` gets built: new tables, new endpoints, the auth swap, the event/snapshot write path, and the four new screens. It assumes TDD v4 (`docs/TDD.md`) as the baseline and calls out deltas rather than restating unchanged material — §4.4–§4.15 and §7.1–§7.4 of TDD v4 (data model, scoring, roadmap assembly, project/submit flow, the re-sort animation) are **unchanged and not repeated here**.

**The two v4 invariants still hold, plus one new one:**

1. **Skills are the only source of truth.** Unchanged. The Skills and Projects screens are new *views* over existing tables — they add no new skill semantics.
2. **Three model call types, then arithmetic.** Unchanged, and now explicitly frozen: V2 adds zero model calls. `event` and `fit_snapshot` are arithmetic and bookkeeping, not AI output.
3. **New: identity is a real credential, not a capability.** V1's `current_student` treated a UUID as a bearer capability (TDD v4 §2, §4.3 — "whoever presents it can read and tick that student's roadmap"). V2 replaces that with `current_user`, resolved from a hashed session token, and `current_student` becomes a *derived* lookup (`user → student`) that every existing router keeps depending on unchanged — see §4.3.

---

## 2. System context

```
┌──────────────┐   fetch + Authorization: Bearer <token>   ┌──────────────┐
│    React     │ ─────────────────────────────────────────▶ │   FastAPI    │
│    (Vite)    │ ◀────────────────── JSON ────────────────── │              │
└──────────────┘                                            └──────┬───────┘
      localStorage holds                                           │
      the session token only                    ┌────────────────────────────┐
      (never the password)                       │         Postgres /         │
                                                  │         SQLite              │
                                                  │  user · session · event ·   │
                                                  │  fit_snapshot  (new)        │
                                                  │  + every V1 table,          │
                                                  │  unchanged                  │
                                                  └────────────────────────────┘
```

No new external service. **Gemini is not in this diagram** — nothing in V2 calls it.

**Trust boundaries, changed from v4.** The browser now holds a session token instead of a raw student id. A token is opaque; only its SHA-256 hash is stored server-side (§4.4), so a DB read can't hand back something replayable. Passwords never leave `POST /api/auth/signup` / `/login` and are hashed with bcrypt before the first `session.add`.

---

## 3. Repository layout

Additions to the TDD v4 tree (`docs/TDD.md` §3) only — nothing existing moves.

```
anchor/
├── docs/
│   ├── PRD-V2.md · TDD-V2.md          # this pair — product / technical truth for V2
│   └── ...                            # v4 docs unchanged
├── backend/
│   ├── app/
│   │   ├── models.py                  # + User, Session, Event, FitSnapshot, LoginFailure; Student.user_id  ← shared
│   │   ├── schemas.py                 # + auth/dashboard/skills/projects request/response models          ← shared
│   │   ├── auth.py                    # bcrypt hash/verify, token issue, current_user, current_student (Salman)
│   │   ├── events.py                  # record_tick, record_submission, snapshot_changed_roles (Umer, V2 lane)
│   │   ├── routers/
│   │   │   ├── auth.py                # POST /signup /login /logout /logout_all (Salman)
│   │   │   ├── dashboard.py           # GET /api/dashboard (Umer)
│   │   │   ├── skills.py              # GET /api/skills (Umer)
│   │   │   └── projects.py            # GET /api/projects (Umer)
│   │   └── analysis/                  # UNCHANGED — frozen for V2, Umer's file-level ownership stays but no edits expected
│   └── tests/
│       ├── test_auth.py               # signup, login, bad password, expiry, claim-on-signup, rate limit
│       └── test_events.py             # tick/untick/submission/pass write the right rows; snapshot only on change
└── frontend/                          # ← BUILT (2026-09-04, Wahab) — frontend-only, fixture-backed;
    ├── src/                          #   see §7.5 for what that means and the corrections below
    │   ├── app/
    │   │   ├── router.tsx             # + /login /signup /dashboard /skills /projects; /onboarding is its
    │   │   │                          #   OWN top-level route, NOT nested under AppShell — see §7.2
    │   │   ├── AppShell.tsx           # rebuilt: sidebar only, no topbar (§7.2) — replaces the current top-bar-only shell
    │   │   └── RequireAuth.tsx        # route guard: no token → /login; no analysis yet → /onboarding
    │   ├── lib/
    │   │   ├── auth.ts                # token + cached user + onboarded flag + a mock account store
    │   │   │                          #   (extends identity.ts's pattern) — see §7.5, /api/auth/* doesn't exist yet
    │   │   ├── eventLog.ts            # NEW, not in the original plan — frontend-only Event/FitSnapshot
    │   │   │                          #   simulation so the Dashboard reacts without a backend; see §7.5
    │   │   └── api.ts                 # Authorization: Bearer instead of X-Student-Id; 401 → clear token, /login
    │   ├── features/
    │   │   ├── auth/                  # AuthCard (shared card layout), LoginPage, SignupPage
    │   │   ├── onboarding/            # OnboardingRoute + StepHeader; SetupPage now split into real
    │   │   │                          #   Courses/Interests steps (see §7.2) + unmodified AnalyzingPage
    │   │   ├── dashboard/             # DashboardPage, StatCards, FitChart, NextActions, ActivityFeed
    │   │   ├── skills/                # SkillsPage, StatusPill (no separate SkillTable — one inline list)
    │   │   └── projects/              # ProjectsPage, ProjectCard, SubmissionHistory
    │   │                              #   (features/profile/ removed 2026-09-04 — DECISIONS #85)
    │   └── styles/tokens.css          # new: type scale, spacing, radii (colors already exist in index.css)
```

### 3.1 Ownership

V1's rule — **one owner per file, lanes don't overlap** — carries over unchanged in mechanism. What changes is Umer's assignment: `backend/app/analysis/` is frozen for V2 (PRD-V2 §2 non-goals — no new model calls), so instead of sitting idle, Umer's V2 lane is the new **event/snapshot/aggregation backend surface** — pure Python and SQL, no model calls, same "nobody else edits it, one clean import boundary" shape his v4 lane had.

| Lane | Owner | Paths |
|---|---|---|
| Auth + identity | **Salman** | `backend/app/auth.py`, `routers/auth.py`, `User`/`Session`/`LoginFailure` rows in `models.py`, storage/deploy config (§9) — a direct extension of his v4 ownership of `db.py`/`identity.py`/`models.py` |
| Events, snapshots, aggregation | **Umer** | `backend/app/events.py`, `routers/dashboard.py`, `routers/skills.py`, `routers/projects.py`, `Event`/`FitSnapshot` rows in `models.py` — **`backend/app/analysis/` itself gets zero V2 edits** |
| Frontend | **Wahab** | `frontend/**` in full, unchanged from v4 — all four new screens, the shell rebuild, the token pass, and the roadmap re-skin |
| Shared | all, via `contract:` PR | `docs/CONTRACT.md`, `models.py`, `schemas.py`, `types.ts` — same rule as v4 |

`Student.user_id`, the `/progress` and `/submit` transactional writes to `event`/`fit_snapshot`, and the `current_student` swap are the three places Salman's and Umer's lanes touch the same files as each other and as the existing V1 routers — call these out explicitly in review rather than treating them as "someone else's file."

### 3.2 Integration seams

| Seam | Producer | Consumer | Done when |
|---|---|---|---|
| `app.auth.current_user(token) -> User` and `app.auth.current_student(user) -> Student` | Salman | Every existing router (`roadmap.py`, `progress.py`, `project.py`, `submit.py`) via a one-line `Depends` swap | Signature and returned `Student` shape unchanged from v4 — no router body changes required |
| `app.events.record_tick(...)`, `record_submission(...)`, `snapshot_changed_roles(...)` | Umer | Salman's `routers/progress.py`, `routers/submit.py` (called inside their existing transaction) | Called with the before/after fit maps for affected roles only; committed in the same `session.commit()` as the tick/submission itself |
| `GET /api/dashboard`, `/api/skills`, `/api/projects` | Umer | Wahab's Dashboard/Skills/Projects pages | Shapes match `docs/CONTRACT.md`'s V2 addendum; Umer ships against `contracts/fixtures/dashboard_response.json` before Wahab needs the real endpoint, same pattern as v4's `roadmap_response.json` seam |
| `POST /api/auth/signup` `/login` `/logout` `/logout_all` | Salman | Wahab's `lib/auth.ts` | Token round-trips; claim-on-signup verified against a real V1-style anonymous `student_id` |

---

## 4. Backend design

### 4.1 Config additions

```python
# app/config.py — additive to TDD v4 §4.1
class Settings(BaseSettings):
    ...
    SESSION_TTL_DAYS: int = 30
    LOGIN_RATE_LIMIT: int = 10          # failures per email per window
    LOGIN_RATE_WINDOW_MIN: int = 15
```

Nothing about `DATABASE_URL`, `LLM_PROVIDER`, or any Gemini/Anthropic setting changes — V2 doesn't touch the model client.

### 4.2 Data model additions

```python
# app/models.py — additive to TDD v4 §4.4, same conventions (new_id, now, JSON columns)

class User(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(unique=True, index=True)     # stored lowercased
    password_hash: str
    name: str
    # NOT semester — corrected 2026-09-04. Semester belongs to Student (below), asked once
    # during onboarding's Courses step, not at signup — the original draft put it on both,
    # which is exactly the "asked twice" bug direct user feedback caught.
    created_at: datetime = Field(default_factory=now)
    last_seen_at: datetime = Field(default_factory=now)

class Session(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(unique=True, index=True)   # sha256 hex of the bearer token; token itself never stored
    created_at: datetime = Field(default_factory=now)
    expires_at: datetime

class Event(SQLModel, table=True):
    """Append-only. Written inside the same transaction as the action it records."""
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    type: str                            # "tick" | "untick" | "submission" | "pass"
    skill_id: str | None = Field(default=None, foreign_key="skill.id")
    role_id: str | None = Field(default=None, foreign_key="role.id")
    submission_id: str | None = Field(default=None, foreign_key="submission.id")
    created_at: datetime = Field(default_factory=now, index=True)

class FitSnapshot(SQLModel, table=True):
    """One row per (user, role) whenever that role's fit_percent actually changes.
    No backfill — history starts at V2 deploy (PRD-V2 §6.1)."""
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    role_id: str = Field(foreign_key="role.id")
    fit_percent: int
    created_at: datetime = Field(default_factory=now, index=True)

class LoginFailure(SQLModel, table=True):
    """Naive rate-limit counter (PRD-V2 §5) — a row per failed attempt, no Redis."""
    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True)
    created_at: datetime = Field(default_factory=now)
```

**Changed table:**

```python
class Student(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str | None = Field(default=None, foreign_key="user.id", index=True)   # NEW, nullable
    name: str
    semester: int
    interests: list[str] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
```

`user_id` is nullable because `POST /api/students` (v4, unchanged) still creates anonymous students during onboarding, exactly as today — it's only set once, either by onboarding-under-an-account or by claim-on-signup (§5.1). Every other V1 table (`Analysis`, `Skill`, `Role`, `Progress`, `Project`, `Submission`, …) is untouched; they already hang off `student_id`, and `current_student` still resolves to the same `Student` row shape (§4.3), so none of them need to know accounts exist.

### 4.3 Identity: `current_user` and the `current_student` swap

```python
# app/auth.py (Salman)
import hashlib, secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException
from passlib.hash import bcrypt
from sqlmodel import Session as DbSession, select

from app.config import settings
from app.db import get_session
from app.models import LoginFailure, Session as SessionRow, Student, User


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(db: DbSession, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(SessionRow(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.SESSION_TTL_DAYS),
    ))
    db.commit()
    return token


def current_user(
    authorization: str | None = Header(default=None),
    db: DbSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or malformed Authorization header")
    row = db.exec(
        select(SessionRow).where(SessionRow.token_hash == hash_token(authorization.removeprefix("Bearer ").strip()))
    ).first()
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "Invalid or expired session")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(401, "Invalid session")
    return user


def current_student(
    user: User = Depends(current_user),
    db: DbSession = Depends(get_session),
) -> Student:
    """Replaces app/identity.py's current_student (TDD v4 §4.3) at the same import path.
    Every existing router already does `student: Student = Depends(current_student)` —
    this keeps that signature and the returned Student shape identical, so roadmap.py,
    progress.py, project.py, and submit.py need a one-line import change and nothing else."""
    student = db.exec(select(Student).where(Student.user_id == user.id)).first()
    if not student:
        raise HTTPException(404, "No student profile yet — complete onboarding")
    return student
```

`app/identity.py`'s v4 `current_student` (header-based) is deleted; `app/auth.py` becomes the single import site every router pulls `current_student` from. This is the one call-site change v4's routers need — no router body touches `student` any differently than it did in TDD v4 §4.8–§4.15.

Rate limiting reads `LoginFailure` rows created in the last `LOGIN_RATE_WINDOW_MIN` minutes for the attempted email; ≥ `LOGIN_RATE_LIMIT` → `429` before checking the password at all.

### 4.4 Auth routes

```python
# app/routers/auth.py (Salman)
router = APIRouter(prefix="/api/auth")

@router.post("/signup")
def signup(body: SignupRequest, db: Session = Depends(get_session)):
    email = body.email.strip().lower()
    if db.exec(select(User).where(User.email == email)).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=email, password_hash=bcrypt.hash(body.password), name=body.name)
    db.add(user); db.commit()

    if body.claim_student_id:
        student = db.get(Student, body.claim_student_id)
        if student and student.user_id is None:      # never steal an already-claimed student
            student.user_id = user.id
            db.add(student); db.commit()

    # No session issued here (corrected 2026-09-04) — signup only ever creates the account.
    # The client always sends the student to /login next; a session is established by an
    # actual login, signup included. This is a product decision, not a security one.
    return {"user": UserOut.from_row(user)}

@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_session)):
    email = body.email.strip().lower()
    if recent_failures(db, email) >= settings.LOGIN_RATE_LIMIT:
        raise HTTPException(429, "Too many attempts — try again later")
    user = db.exec(select(User).where(User.email == email)).first()
    if not user or not bcrypt.verify(body.password, user.password_hash):
        db.add(LoginFailure(email=email)); db.commit()
        raise HTTPException(401, "Wrong email or password")     # never say which was wrong
    user.last_seen_at = datetime.now(timezone.utc)
    db.add(user); db.commit()
    return AuthResponse(token=issue_session(db, user), user=UserOut.from_row(user))

@router.post("/logout")
def logout(authorization: str = Header(), db: Session = Depends(get_session)):
    db.exec(delete(SessionRow).where(SessionRow.token_hash == hash_token(authorization.removeprefix("Bearer ").strip())))
    db.commit()
    return {"ok": True}

@router.post("/logout_all")
def logout_all(user: User = Depends(current_user), db: Session = Depends(get_session)):
    db.exec(delete(SessionRow).where(SessionRow.user_id == user.id))
    db.commit()
    return {"ok": True}
```

`last_seen_at` is only bumped on login — **not** on every request — because it is the dashboard delta's baseline (§4.6) and must stay fixed for the whole session, not creep forward as the student uses the app.

### 4.5 Event + snapshot writer

```python
# app/events.py (Umer, V2 lane — no model calls, plain SQL bookkeeping)
from app.models import Event, FitSnapshot

def record_tick(db, user_id: str, skill_id: str, checked: bool) -> None:
    db.add(Event(user_id=user_id, type="tick" if checked else "untick", skill_id=skill_id))

def record_submission(db, user_id: str, role_id: str, submission_id: str, passed: bool) -> None:
    db.add(Event(user_id=user_id, type="submission", role_id=role_id, submission_id=submission_id))
    if passed:
        db.add(Event(user_id=user_id, type="pass", role_id=role_id, submission_id=submission_id))

def snapshot_changed_roles(db, user_id: str, before: dict[str, int], after: dict[str, int]) -> None:
    """One row per role whose fit_percent actually changed. Typically 1-8 rows —
    only roles containing the ticked skill (or the project's verified skills) move."""
    for role_id, new_fit in after.items():
        if before.get(role_id) != new_fit:
            db.add(FitSnapshot(user_id=user_id, role_id=role_id, fit_percent=new_fit))
```

Called from inside the *existing* transactions, not as separate requests:

```python
# app/routers/progress.py — delta from TDD v4 §4.11
@router.post("/api/progress")
def set_progress(body: ProgressRequest, user=Depends(current_user),
                  student=Depends(current_student), db=Depends(get_session)):
    before = fit_by_role(db, student)                 # only roles containing body.skill_id change
    if body.checked:
        db.execute(insert(Progress).values(...).on_conflict_do_nothing(...))
    else:
        db.execute(delete(Progress).where(...))
    record_tick(db, user.id, body.skill_id, body.checked)
    after = fit_by_role(db, student)
    snapshot_changed_roles(db, user.id, before, after)
    db.commit()
    return {"ok": True}
```

`fit_by_role` is a small helper that reuses `scoring.fit_percent` and the same query shapes `build_roadmap` already computes (TDD v4 §4.10) — restricted to roles containing the changed skill, so this stays 1-8 rows and a handful of extra queries, not a full roadmap rebuild. `routers/submit.py` gets the identical pattern: snapshot before/after around the existing `Submission` insert, plus `record_submission`.

### 4.6 Dashboard (`GET /api/dashboard`, Umer)

```python
# app/routers/dashboard.py
@router.get("/api/dashboard")
def get_dashboard(user=Depends(current_user), student=Depends(current_student), db=Depends(get_session)):
    roadmap = build_roadmap(db, student)                          # reuse v4's assembly verbatim
    top3 = roadmap.roles[:3]

    events_since = db.exec(select(Event).where(Event.user_id == user.id,
                                                Event.created_at >= user.last_seen_at)).all()
    verified_delta = sum(1 for e in events_since if e.type == "pass")
    checked_delta = (sum(1 for e in events_since if e.type == "tick")
                     - sum(1 for e in events_since if e.type == "untick"))

    snapshots = {r.id: db.exec(select(FitSnapshot)
                               .where(FitSnapshot.user_id == user.id, FitSnapshot.role_id == r.id)
                               .order_by(FitSnapshot.created_at)).all()
                for r in top3}

    recent = db.exec(select(Event).where(Event.user_id == user.id)
                     .order_by(Event.created_at.desc()).limit(10)).all()

    return DashboardResponse(
        top_role=top3[0] if top3 else None,
        skills_verified=len(verified_ids(db, student)),          # reuse v4's helper, TDD §4.15
        skills_checked=len(checked_ids(db, student)),
        verified_delta=verified_delta, checked_delta=checked_delta,
        snapshots={rid: [SnapshotPoint(fit=s.fit_percent, at=s.created_at) for s in rows]
                  for rid, rows in snapshots.items()},
        next_actions=[next_action_for(r, roadmap) for r in top3],
        recent_events=[humanize(e, db) for e in recent],
    )
```

`next_action_for(role, roadmap)`: the role's highest-weight unresolved skill (`core` before `supporting`, then declared order), or — if the role has a project with no passing submission — `"Finish {project.title} — verifies {n} skills"`. Both branches read data `build_roadmap` already assembled; no new query shape.

`humanize(event, db)` turns an `Event` row into the Dashboard's activity-feed sentence ("Verified *SQL Query Optimization* via repo review", "Marked *Docker Basics* as learned") by joining `skill_id`/`role_id` back to their names — a lookup, not a stored string, so renames upstream never go stale in old events.

### 4.7 Skills inventory (`GET /api/skills`, Umer)

```python
@router.get("/api/skills")
def list_skills(student=Depends(current_student), db=Depends(get_session)):
    roadmap = build_roadmap(db, student)              # skills[] already carries checked/verified/coverage
    roles_by_skill: dict[str, list[dict]] = defaultdict(list)
    for role in roadmap.roles:
        for rs in role.skills:
            roles_by_skill[rs.skill_id].append({"id": role.id, "title": role.title})
    return {"skills": [SkillInventoryRow(**s.model_dump(), roles=roles_by_skill[s.id])
                       for s in roadmap.skills]}
```

Status pill is derived client-side from the same three booleans/fields the Roadmap drawer already reads (`verified` → Verified, `checked` → Learned, `coverage_depth == "full"` → Covered, `"partial"` → Partial, else Missing) — no new server-side status enum, one more place invariant #1 shows up.

### 4.8 Projects with history (`GET /api/projects`, Umer)

```python
@router.get("/api/projects")
def list_projects(student=Depends(current_student), db=Depends(get_session)):
    projects = db.exec(select(Project).where(Project.student_id == student.id)).all()
    out = []
    for p in projects:
        subs = db.exec(select(Submission).where(Submission.project_id == p.id)
                       .order_by(Submission.created_at.desc())).all()
        out.append(ProjectWithHistory(
            project=ProjectResponse.from_row(p, db),
            submissions=[SubmissionOut.from_row(s) for s in subs],
        ))
    return {"projects": out}
```

This is the **only** net-new backend surface the Projects screen needs (PRD-V2 §4.6) — `POST /api/submit` (resubmission) and the whole fetch → review → score pipeline are TDD v4 §4.13–§4.15, untouched.

---

## 5. Runtime flows

### 5.1 Signup with claim-on-signup

**Corrected 2026-09-04:** signup no longer issues a session — see the `POST /signup` handler in
§4.4 and PRD-V2 §4.1. The flow now always routes through an actual login:

```
Browser (has V1 anchor:student_id in localStorage, or doesn't)
   │
   ├─ POST /api/auth/signup {email, password, name, claim_student_id?}
   │       claim_student_id = localStorage's anchor:student_id, read once at signup time
   │
   FastAPI  ├─ create User, bcrypt-hash password
            ├─ if claim_student_id: Student.user_id = user.id  (only if unclaimed)
            │
   ◀────────┤ { user }                                    (no token)
   │
   ├─ lib/auth.ts clears anchor:student_id (claimed or not — it's spent); does NOT store a session
   └─ → /login, with the email prefilled

Browser
   │
   ├─ POST /api/auth/login {email, password}
   FastAPI  └─ issue_session → token
   ◀────────┤ { token, user }
   │
   ├─ lib/auth.ts stores the token
   └─ → /onboarding if this account has no analysis yet, else → /
```

Login **never** claims — only signup reads `claim_student_id`, matching PRD-V2 §4.1. Whether an
account lands on `/onboarding` or `/` after login depends on that specific account's own state
(claimed-at-signup, or a previously completed onboarding) — never on a single global flag, since
two different accounts on the same browser must be told apart.

### 5.2 Tick → event + snapshot (extends TDD v4 §5.2)

```
User ticks a skill in the drawer
   │
   ├─▶ setState: toggle skillId in checkedIds        ← unchanged, still synchronous, still local
   │      └─ re-sort, ring animation, WhatMoved — identical to v4, driven by the same useMemo
   │
   └─▶ fetch POST /api/progress   (fire and forget, unchanged from v4)
          └─ server: fit_by_role before → Progress upsert/delete → record_tick →
             fit_by_role after → snapshot_changed_roles → one commit
```

**Nothing about the animation changes.** The event/snapshot write is invisible to the client — it doesn't wait for it, doesn't render anything from it. It only becomes visible later, on the Dashboard.

### 5.3 Submit → event + snapshot (extends TDD v4 §5.3)

Identical shape to §5.2: `fit_by_role` before the `Submission` insert, `record_submission`, `fit_by_role` after, `snapshot_changed_roles`, one commit — added to `routers/submit.py`'s existing transaction (TDD v4 §4.15) without changing its response shape or timing.

### 5.4 Dashboard load

```
GET /api/dashboard  (Authorization: Bearer <token>)
   │
   ├─ current_user → current_student → build_roadmap()   (same assembly as /roadmap)
   ├─ events since user.last_seen_at → deltas
   ├─ fit_snapshot rows for top-3 roles → chart series
   ├─ last 10 events → activity feed
   └─ one payload, one fetch — same "everything in one response" rule as /roadmap (TDD v4 §4.10)
```

### 5.5 Resume (changed from TDD v4 §5.4)

On mount: read the session token from `localStorage`. None → `/login`. Token present → any authenticated `GET` (e.g. `/api/dashboard`) — `200` → land on the requested/default page; `401` → clear the token, `/login`; `404` (no student/analysis yet, from `current_student`) → `/onboarding`.

---

## 6. API contracts (V2 additions)

All under `/api`, all requiring `Authorization: Bearer <token>` except `/auth/signup` and `/auth/login`.

### `POST /auth/signup` → 200

**No `semester`, no `token` in the response — corrected 2026-09-04, see §4.4/§5.1.**

```json
{ "email": "ayesha@example.com", "password": "at-least-8-chars", "name": "Ayesha",
  "claim_student_id": "stu_9f…" }
```
→ `{ "user": { "id": "usr_1a", "email": "…", "name": "Ayesha", "created_at": "…" } }`
Errors: `409` email already registered.

### `POST /auth/login` → 200

```json
{ "email": "ayesha@example.com", "password": "…" }
```
→ `{ "token": "…", "user": { "id": "usr_1a", "email": "…", "name": "Ayesha", "created_at": "…" } }`
— the only auth response that carries a token; only a login (signup included, one hop later)
establishes a session. Errors: `401` "Wrong email or password" (never which) · `429` rate-limited.

### `POST /auth/logout` → 200 `{ "ok": true }` · `POST /auth/logout_all` → 200 `{ "ok": true }`

### `GET /dashboard` → 200

```json
{
  "top_role": { "id": "ro_b2", "title": "Data Engineer", "fit_percent": 71 },
  "skills_verified": 6, "skills_checked": 11,
  "verified_delta": 2, "checked_delta": 9,
  "snapshots": { "ro_b2": [ { "fit": 48, "at": "2026-08-20T…" }, { "fit": 71, "at": "2026-09-02T…" } ] },
  "next_actions": [ { "role_id": "ro_b2", "label": "Learn Airflow Basics", "kind": "tick" } ],
  "recent_events": [ { "text": "Verified SQL Query Optimization via repo review", "at": "2026-09-02T…" } ]
}
```

### `GET /skills` → 200

```json
{ "skills": [ { "id": "sk_a1", "name": "SQL Query Optimization", "status": "verified",
               "source": "repo review", "roles": [ { "id": "ro_b2", "title": "Data Engineer" } ] } ] }
```

### `GET /projects` → 200

```json
{ "projects": [ { "project": { "id": "pr_9d", "role_id": "ro_b2", "title": "…", "spec": "…" },
                 "submissions": [ { "repo_url": "…", "total": 5, "max_total": 6, "passed": true,
                                   "created_at": "…" } ] } ] }
```

Everything from TDD v4 §6 (`/courses`, `/students`, `/analyze`, `/roadmap`, `/progress`, `/project`, `/submit`) is **unchanged in shape** — only the auth header changes, per router.

---

## 7. Frontend design

### 7.1 Token storage and the auth API wrapper

```ts
// lib/auth.ts (Wahab) — parallels lib/identity.ts's role, doesn't replace it outright;
// identity.ts still exists for the pre-signup anonymous student_id used in claim-on-signup
const TOKEN_KEY = "anchor:token";

export function getToken(): string | null { return localStorage.getItem(TOKEN_KEY); }
export function setToken(t: string): void { localStorage.setItem(TOKEN_KEY, t); }
export function clearToken(): void { localStorage.removeItem(TOKEN_KEY); }

export async function signup(body: SignupRequest) { /* POST /api/auth/signup, setToken(res.token) */ }
export async function login(body: LoginRequest) { /* POST /api/auth/login, setToken(res.token) */ }
export async function logout() { /* POST /api/auth/logout, clearToken() */ }
```

```ts
// lib/api.ts — delta from TDD v4 §7.5
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${import.meta.env.VITE_API_URL}${path}`, {
    ...init,
    signal: AbortSignal.timeout(240_000),
    headers: { "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init.headers },
  });
  if (res.status === 401) { clearToken(); window.location.assign("/login"); throw new ApiError(401, "session expired"); }
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

Same "one `fetch`, no React Query" rule as v4 (`frontend/CLAUDE.md`) — the only change is which header carries identity and what a `401` does.

### 7.2 App shell and routing

**Corrected from the original draft (2026-09-04, Wahab):** the code sample this section originally
shipped nested `/onboarding` *inside* the `RequireAuth><AppShell>` group, which silently
contradicts PRD-V2 §3's "`/onboarding (post-signup, no sidebar: …)`" — a sidebar-wrapped route
cannot be a no-sidebar route. Implementation follows the PRD: `/onboarding` is its own top-level
route, sitting behind `RequireAuth` but never inside `AppShell`.

```tsx
// app/router.tsx — delta from TDD v4 §3
export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/signup", element: <SignupPage /> },
  {
    path: "/onboarding",
    element: <RequireAuth><OnboardingRoute /></RequireAuth>,   // no AppShell — PRD-V2 §3, "no sidebar"
  },
  {
    element: (
      <RequireAuth>
        <AnalysisProvider>                                     {/* lifted here — see below */}
          <AppShell />                                          {/* sidebar only — no topbar, see §7.2 */}
        </AnalysisProvider>
      </RequireAuth>
    ),
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/roadmap", element: <RoadmapPage /> },           // unchanged component, re-skinned only
      { path: "/skills", element: <SkillsPage /> },
      { path: "/projects", element: <ProjectsPage /> },
      // no /profile — the screen was built then removed, DECISIONS #85
    ],
  },
]);
```

`RequireAuth` checks `getToken()`; absent → redirect `/login`. Token present but no analysis yet
(`isOnboarded()` false) and not already on `/onboarding` → redirect `/onboarding`. `AppShell.tsx`
is rebuilt: 232px fixed sidebar (logo, nav items with active-route highlight, an account row at
the bottom). The current minimal top-bar-only shell (which has an explicit "no nav links, no
login" comment tied to v4's PRD §10) is replaced outright — that comment described v4 scope, not
a permanent constraint.

**No topbar — corrected 2026-09-04, direct user feedback.** The original draft here specified a
topbar (page title read from each route's `handle: { title }`, plus a user-chip → dropdown menu
with Profile/Log out). It's removed outright: every screen already renders its own in-content
heading (Dashboard's "Welcome back, …", Roadmap's student header, Skills'/Projects' own `<h1>`),
so the topbar's title duplicated something already on the page. Its log-out job moves into the
sidebar instead of a second chrome bar: a dedicated icon button (`lucide-react`'s `LogOut`, styled
`text-anchor-critical` — red is a deliberate, one-off exception to `anchor-design`'s "critical is
for missing-core badges only" rule, since a destructive action button is exactly the kind of place
a status color is allowed to mean something different) next to a plain, non-interactive account row
(avatar + name, no link) at the sidebar's bottom. The `DropdownMenu` component this replaced is no
longer used anywhere; it's left in `components/ui/dropdown-menu.tsx` rather than deleted, in case a
later screen needs one — shadcn output is meant to be added once and reused, not re-generated per
feature. Route `handle: { title }` values are gone from `router.tsx` along with the topbar that
read them.

**`/profile` built, then removed — corrected 2026-09-04, DECISIONS #84 then #85.** The topbar's
other job (a Profile link) briefly became a `NavLink` on the account name, then — direct feedback
said not to make the name a button — its own item in `NAV_ITEMS`. Next message: "remove profile
page" outright. So there is no Profile screen and no way to reach one: the account row is avatar +
name as plain text, nothing more, and `features/profile/` is deleted. `logoutAll()` (`lib/auth.ts`)
is deleted with it — it was only ever called from that screen's "Log out everywhere" button, and in
this mock single-session store it did nothing `logout()` didn't already do.

**New, not in the original draft: `AnalysisProvider` is lifted** from being scoped inside
`RoadmapPage.tsx` (TDD v4's pattern) up to wrap the whole `AppShell`-nested route group above.
PRD-V2 §4.5 requires the Skills screen's ticking to use "the same optimistic path as the drawer"
— that only works if `/roadmap` and `/skills` share one `AnalysisContext` instance instead of each
fetching and re-deriving their own. `RoadmapPage.tsx` no longer wraps itself in `AnalysisProvider`.

`/onboarding` renders `SetupPage` and `AnalyzingPage`, wrapped in a step header (Courses →
Interests → Analysis) that tracks which one is actually active — `OnboardingStep` now has three
real values, and `StepHeader` has no more "Interests lights up together with Courses" special
case. `AnalyzingPage` is unmodified beyond one small, necessary addition: an optional
`onSuccess?: () => void` prop — mirroring the `onComplete` prop `SetupPage` already had — called
instead of its hardcoded `navigate("/roadmap")` when supplied. Without it, `OnboardingRoute` had
no way to mark the account onboarded before navigating, and `RequireAuth` would bounce the student
straight back to `/onboarding` in a redirect loop. Omitting the prop preserves `AnalyzingPage`'s
exact V1 behavior.

**`SetupPage` itself is *not* unmodified — corrected 2026-09-04, direct user feedback that the
original "one long form, 3-step header only decorative" design was wrong:**

- Takes a `step: "courses" | "interests"` prop and renders only that half; all state
  (catalog, selections, custom courses, interests) lives in one component instance that persists
  across the step transition, so nothing is lost going back and forth. `onContinue`/`onBack` swap
  the step; the interests step's "Analyze my path" button is what used to be the single submit.
- The "Your name" field is gone — the account's name (`lib/auth.ts`'s `getUser()`) is sent to
  `POST /api/students` directly. Semester stays, now the only field at the top of the Courses step.
- `CourseCard.tsx` gained a full-outline preview (a "Read full outline" toggle, viewable whether
  or not the course is picked) and, for any catalog course carrying `curriculum_variants`, an
  outline picker (Standard / each named variant / "Write my own") — replacing the old
  always-available-but-hidden single override textarea. `CourseSelection` changed shape from
  `{ semester_tag, override }` to `{ semester_tag, outline, customText }`, where `outline` is
  `"default"`, `"custom"`, or a variant id; `resolveOverride()` in `SetupPage.tsx` turns that into
  the same `curriculum_override` string the request already sent. A selected variant's or the
  custom text's resolved content is always shown back, read-only for variants, editable for
  custom — "what will be analyzed" is never a guess. A catalog course picking "Write my own" is
  held to the same `MIN_CUSTOM_CURRICULUM_CHARS` (50) the fully-custom "add a course not listed"
  path already enforced; before this it wasn't validated at all.

### 7.3 New screens — component shape, not full spec

PRD-V2 §4.3–§4.7 already specifies what each screen shows; this section is only the technical shape.

- **`features/dashboard/`** — `DashboardPage` fetches `/api/dashboard` once on mount (same "one fetch" rule). `FitChart` renders `snapshots` as an SVG line — **no new charting dependency**: `FitRing` already proves an inline-SVG approach works for this codebase (TDD v4 §7.3), and a 3-line time series is a `<polyline>` with a scaled x/y, not a library job. Colors are the `dataviz` skill's validated categorical palette, dark-mode slots 1-3 (blue/orange/aqua), not a new ad hoc choice. If a richer chart is wanted later, that's a `contract:`-style note in `docs/DECISIONS.md`, not a default. Gridlines + `%` labels and a per-series gradient fill were added on top of the bare polylines (DECISIONS #72/#73) — the fill hugs each line at a fixed depth rather than washing down to the 0% baseline, since three lines sitting close together (a typical case) blend into a muddy overlap otherwise. **Current numbers** (top-role fit, verified/checked counts) read live off the shared `AnalysisContext`, never off the fetched payload — see §7.5 for why. The `<svg>`'s `viewBox`/`width`/`height` are set to the container's **measured** pixel width (`ResizeObserver`), not a fixed constant scaled via `preserveAspectRatio="none"` — that non-uniform stretch (DECISIONS #75) turned round markers into ~2.2×-wide ellipses and warped the gridline text, reading as a scaled bitmap rather than crisp vector UI. Measuring the container keeps one SVG unit equal to one CSS pixel on both axes. **`NextActions`
restyled as colored task cards** (2026-09-04, DECISIONS #90) — the original three identical
plain-bordered cards were indistinguishable except by label text; each now carries `FitChart`'s
same categorical color for its role (`COLORS[i % 3]`, `i` matching `top3`'s index, the same array
both components map over), as a 4px left accent bar plus the role title as a colored eyebrow above
the action label, with a hover-animated `ArrowUpRight` icon — a second consumer of `FitChart.tsx`'s
existing palette, not re-validated separately, linking each "what now" card back to its line in the
chart directly above it. `nextActions` in `DashboardPage.tsx` gained a `roleTitle` field
(`role.title`) to render the eyebrow; `label` (the existing "Learn X" / "Review Y" text) is
unchanged.
- **`features/skills/`** — `SkillsPage` fetches `/api/skills` once; filter tabs and search are client-side `useMemo` over the returned array, no server round-trip per keystroke. Ticking reuses the exact optimistic path `RoleDrawer` already has (`toggle(skillId)` in `AnalysisContext`) — the Skills screen needs `AnalysisContext` mounted the same way the Roadmap page does, which is exactly what §7.2's provider lift is for. Status labels reuse `SkillRow.tsx`'s exported `skillState()` (DECISIONS #34's precedence), not a re-derived enum, so this screen can't disagree with the drawer about a skill's state. Built as one inline list rather than a separate `SkillTable` component — no table primitive exists elsewhere in this codebase, and introducing one for a single screen wasn't warranted.
- **`features/projects/`** — `ProjectsPage` fetches `/api/projects` once; resubmit calls the existing `submitRepo(roleId, url)` context function unchanged, then refetches `/api/projects` (cheap, not on the hot animation path).
- ~~**`features/profile/`**~~ — built, then removed outright, DECISIONS #85. Log out lives in `AppShell.tsx`'s sidebar instead (§7.2); there is no account-info screen and no `logoutAll()` (`lib/auth.ts`) — it had no caller left once the screen was cut.

### 7.4 Design tokens

```css
/* src/styles/tokens.css — new, imported after index.css's existing color tokens */
:root {
  --font-display: "Poppins", ui-sans-serif, system-ui, sans-serif;  /* decided 2026-09-04, revised same day */
  --text-display: 3rem; --text-heading: 2rem; --text-body: 1rem; --text-caption: 0.8125rem;
  /* was 2.5rem/1.25rem/0.9375rem/0.75rem, then --text-heading 1.5rem — bumped twice same day,
     DECISIONS #87 then #88, both direct feedback */
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-6: 24px; --space-8: 32px;
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px;
}
```

**Font decided:** Poppins, loaded via a `<link>` in `index.html` (weights 500/600/700), applied
only to headings, fit %, and dashboard stat numerals (`font-display` Tailwind utility) — body text
stays the system sans stack. (First shipped as Space Grotesk; swapped to Poppins same-day on
direct user feedback — DECISIONS #63.) `tailwind.config.js` gains a matching
`fontFamily.display`/`fontSize` extension pointing at these variables, the same pattern it already
uses for the color tokens. Spacing was **not** extended — Tailwind's default 4px-increment scale
already equals `--space-1..8` (`anchor-design` §4), so `p-1`/`p-4`/`p-6`/etc. already *are* the
token scale.

**Type scale bumped app-wide** (2026-09-04, DECISIONS #87, direct feedback: "increase the entire
app's text sizes, specially for main titles or main content"). Two changes together, not one: (1)
the four `--text-*` tokens above moved up a step each — these already drove every page's `<h1>`
(Dashboard/Roadmap/Skills/Projects, `font-display text-heading`) and the Dashboard's stat numerals
(`font-display text-display`), so those got bigger for free. (2) Everything else on a "main title
or main content" that predates the token system and still carries a raw Tailwind size — the
Login/Signup card title, the onboarding step headings, role/course/project card titles, a role's
one-liner and a skill's real-world description, project specs, submission feedback, and each page's
subtitle line — moved up one Tailwind step by hand (`text-sm`→`text-base`, `text-base`→`text-lg`,
etc.), file by file. Deliberately **not** touched: uppercase-tracking section eyebrows ("Progress,"
"What now," "Your closest paths," …), badges, weight tags, dates, and error text — `anchor-design`
§3's "labels recede, numbers/titles are heroes" rule means these stay small on purpose, and bumping
them would blur the hierarchy the size increase is meant to sharpen.

**Item-level titles corrected back down — same day, DECISIONS #89.** #87's "role/course/project
card titles" step-up turned out too far: a role card's title (and a role's fit-ring numeral), a
project card's title, a course card's title, the Prove It panel's project title, a skill's name in
`SkillRow`/`SkillsPage`, a next-action card's label, and the Dashboard's top-role name under the fit
% — all moved back down one Tailwind step from #87's bump (`text-lg`→`text-base`,
`text-base`→`text-sm`, and the two `FitRing` numerals attached to role cards/drawer to match). Page
`<h1>`s (still on `--text-heading`, further bumped in #88) and body-copy descriptions (a role's
one-liner, a skill's real-world text, project specs, submission feedback) are untouched — the
correction is scoped to item-level *names* inside a list of many, which read as too heavy once
sitting under an even-bigger page title.

**Colors were revised beyond what this section originally shipped** (DECISIONS #72), on the same
direct feedback ("too mono colored"): `index.css`'s `.dark` block now gives `--background`,
`--card`, and `--popover` genuinely distinct values (the stock shadcn dark theme this app started
from had all three identical, plus `--secondary`/`--muted`/`--accent`/`--border`/`--input` all
identical to *each other* — six roles collapsed into two flat surfaces, which is what read as
flat/gray), and `--primary`/`--ring` switched from near-white/gray to the existing brand blue
(`213 77% 56%`, the same hue as `--anchor-adjacent`/`--anchor-ring-fill`) so buttons, focus rings,
and the sidebar's active-nav indicator all carry the one accent PRD-V2 §8 already specified —
that section described the intent in Stage 1 but the token values themselves were never actually
changed from shadcn's defaults until this pass. `--anchor-*` semantic tokens are unchanged.

### 7.5 Interim frontend-only data — no backend yet (new section, 2026-09-04, Wahab)

Everything above assumes `/api/auth/*`, `/api/dashboard`, `/api/skills`, and `/api/projects`
exist. They don't (PRD-V2 §0's audit) — Salman's and Umer's V2 lanes haven't started. Rather than
block the whole frontend build on that, the frontend lane was built **frontend-only,
fixture-backed**, the same `VITE_USE_FIXTURE` pattern TDD v4 used to build the Roadmap screen
before the real backend existed (`lib/api.ts`'s `USE_FIXTURE` branch, restored — it had been
deleted once V1's backend shipped — and extended to serve `contracts/fixtures/dashboard_response.json`,
`skills_response.json`, `projects_response.json`, all newly authored from the existing demo
student in `roadmap_response.json`).

Two problems a static fixture alone doesn't solve, both solved by the same mechanism:

- **`lib/auth.ts`** has no real endpoint to call at all (not "fixture vs. real branch" — there's
  nothing to branch to), so `signup`/`login`/`logout`/`logoutAll` are fully local: a small mock
  account store in `localStorage`, seeded with the demo account (`ayesha@example.com`, any
  password logs in). Swapping in real `POST /api/auth/*` later means rewriting these four function
  bodies; every caller (`LoginPage`, `SignupPage`, `RequireAuth`) keeps the same signatures.
- **The Dashboard would look dead** — PRD-V2 §1 frames the whole feature as "a reason to return,"
  and a chart that never moves after a real tick undercuts that on first use. `lib/eventLog.ts`
  (new, not in the original plan) is a small `localStorage`-backed mirror of §4.2's `Event`/
  `FitSnapshot` tables: `seedIfEmpty()` seeds it once from the dashboard fixture (so day one still
  shows a history), then `AnalysisContext.toggle()`/`submitRepo()` call `recordTick`/
  `recordSubmission`, and a `useEffect` diffing `roleFit` against a `useRef` of its previous value
  — the same technique `WhatMoved.tsx` already uses — calls `recordSnapshotIfChanged` per role
  whose fit actually moved. `GET /api/projects`'s fixture branch does the equivalent for
  submission history, merging any live `recordSubmission` events in ahead of the seeded ones so a
  resubmit shows up on refetch instead of vanishing. Verified live in the browser: ticking a skill
  on `/roadmap` produces a new line in the Dashboard's activity feed and a new chart point on the
  next visit, not just the static seed.

Both are single-browser, `localStorage`-only — no cross-device sync, honestly, since there's no
server. **The seam for real integration is exactly `lib/auth.ts` and `lib/api.ts`'s fixture
branch** — when the real endpoints land, delete `eventLog.ts`, delete the mock account store, and
swap each function body; no screen needs to change, matching this document's existing promise for
the Roadmap screen (§7).

One more small, deliberate deviation: `RoadmapPage.tsx`'s header lost its "Start over" button (it
called `clearStudentId()` and routed to the retired `/setup`). PRD-V2 §2 lists "'Start over' (new
analysis) is V3" as a non-goal — V2 has nowhere for it to go once `/setup` isn't a top-level route
— so removing it is compliance with that non-goal, not a rebuild of the screen (§4.4 still holds:
the re-sort math, drawer, and `ProveIt` states are untouched).

**A second, sharper seam this interim mode exposes — corrected 2026-09-04, DECISIONS #88.** The
`/api/students` fixture branch always returns `{student_id: "fixture-student"}` and `/api/roadmap`
always returns the same static `roadmap_response.json`, regardless of what name was actually typed
at signup or onboarding — there's no real backend yet to persist a per-account student. That's fine
for `checkedIds`/`roleFit`/skills (the demo data those need to demonstrate), but `data.student.name`
being the fixture's hardcoded "Ayesha" reads as a bug once the sidebar's account row started
showing the *real* signed-in name (#83): a student named "Wahab Tariq" would see "Welcome back,
Ayesha" on Dashboard and "Ayesha · Semester 4" on Roadmap right next to a sidebar that correctly
says "Wahab Tariq." Fixed at the two call sites that greet-by-name — `DashboardPage.tsx`'s `<h1>`
and `RoadmapPage.tsx`'s `<h1>` — by preferring `getUser()?.name` (the real authenticated account)
over `data.student.name` (the fixture's), falling back to the fixture name only if `user` is
somehow absent. `data.student.semester` and everything else keyed to the fixture (roles, skills,
interests) is untouched — there's no equivalent "real" source for those yet, so the fixture stays
authoritative for them until `/api/students` and `/api/roadmap` are real.

---

## 8. Configuration

```bash
# backend/.env — additive to TDD v4 §9
SESSION_TTL_DAYS=30
LOGIN_RATE_LIMIT=10
LOGIN_RATE_WINDOW_MIN=15
```

No new frontend env var — `VITE_API_URL` is unchanged; the token lives in `localStorage`, not env config.

---

## 9. Deployment and storage

Per `docs/PRD-V2.md` §6.3 (which the team chose to keep framed as SQLite, with a footnote): the four new tables are created by the same `SQLModel.metadata.create_all(engine)` call TDD v4 §10 already runs on startup — no migration tooling needed either way. If deploying on SQLite, mount a persistent volume and enable WAL (`PRAGMA journal_mode=WAL`, `busy_timeout=5000`) exactly as PRD-V2 §6.3 specifies. `backend/app/db.py` already branches on `DATABASE_URL` to run on Postgres/Supabase instead (TDD v4 §4.2, §9) — if V2 deploys the same way V1 already does, that branch needs no change at all for the new tables.

---

## 10. Error handling (V2 additions to TDD v4 §11)

| Condition | Status | Client behaviour |
|---|---|---|
| Missing/malformed `Authorization` header | 401 | Clear token, redirect `/login` |
| Expired or unknown session token | 401 | Same |
| Wrong email or password | 401 | Inline error, generic message, never says which |
| Login rate-limited | 429 | Inline error: "Too many attempts — try again later" |
| Signup with existing email | 409 | Inline error on the email field |
| `current_student` finds no student for this user | 404 | Redirect `/onboarding` |

Every other row of TDD v4's error table (§11) is unchanged — `/roadmap`, `/progress`, `/project`, `/submit` behave exactly as v4 specifies once `current_student` resolves correctly.

---

## 11. Test plan (V2 additions to TDD v4 §12)

| File | Covers |
|---|---|
| `test_auth.py` | signup creates a user + session; duplicate email → 409; login with wrong password → 401 and writes a `LoginFailure`; 10 failures → 429; claim-on-signup sets `Student.user_id` once and only once; expired session → 401 |
| `test_events.py` | a tick writes exactly one `Event` and, only for roles whose fit changed, one `FitSnapshot`; a tick on an already-fully-covered skill (TDD v4 §4.6's `max` case) writes **no** snapshot; a passing submission writes both a `submission` and a `pass` event |
| `test_dashboard.py` | deltas are computed relative to `last_seen_at`, not "since ever"; `next_action_for` picks the highest-weight unresolved skill correctly |

No test calls the model — unchanged from v4, and even more clearly out of scope since V2 adds no model calls at all.

---

## 12. Build order — two days, three lanes

Mirrors `docs/PRD-V2.md` §9, mapped onto the same three names as TDD v4 §14.

### Day 1 — identity, shell, memory

| Who | Work |
|---|---|
| **Salman** | `User`, `Session`, `LoginFailure` tables; bcrypt; `issue_session`/`current_user`/`current_student` in `app/auth.py`; `routers/auth.py` (signup/login/logout/logout_all); swap every existing router's `current_student` import; claim-on-signup; rate-limit check; storage/deploy config per §9 |
| **Umer** | `Event`, `FitSnapshot` tables; `app/events.py` (`record_tick`, `record_submission`, `snapshot_changed_roles`); wire both into `routers/progress.py` and `routers/submit.py`'s existing transactions; `GET /api/dashboard`, `/api/skills`, `/api/projects` against a hand-written `contracts/fixtures/dashboard_response.json` |
| **Wahab** | `tokens.css` + Tailwind extension (§7.4); `AppShell.tsx` rebuild (sidebar + account row, no topbar — §7.2); `RequireAuth`; `/login`, `/signup` pages; `/onboarding` step wrapper around the existing Setup/Analyzing components |

**Exit criteria (matches PRD-V2 §9):** sign up in browser A, tick a skill, log in from browser B and see it. A V1 anchor:student_id claims correctly on signup. Every authenticated request 401s cleanly with no token, and the client lands on `/login`.

### Day 2 — the screens

| Who | Work |
|---|---|
| **Wahab** | Dashboard UI (stat cards + deltas, `FitChart`, next-action cards deep-linking into the roadmap drawer, activity feed); Skills UI; Projects UI; ~~Profile UI~~ (built, then removed — DECISIONS #85); Roadmap re-skin (re-skin only — TDD v4 §7.2–§7.4 untouched) |
| **Umer** | Iterate `/api/dashboard`, `/api/skills`, `/api/projects` shapes against Wahab's real UI needs; `test_events.py`, `test_dashboard.py` |
| **Salman** | Deploy with the storage choice from §9 verified (log out, redeploy, log back in with data intact); `logout_all` end-to-end check; seed a fresh account and click every screen |
| **All (last 2h)** | Cross-browser loop: signup → onboarding → dashboard → roadmap tick → submit repo → dashboard shows the jump on the chart. **Freeze.** |

**Cut order**, unchanged from PRD-V2 §9: activity feed → skills search/filters → next-action cards (never the chart) → Projects screen collapses to a flat list. Never cut auth correctness or snapshot writes — missing history can't be backfilled.

---

## Appendix — auth design note (supersedes TDD v4 Appendix A)

TDD v4's Appendix A sketched Supabase Auth + ES256 JWT verification as the "if v2 wants accounts" path. **This design does not use it.** `docs/DECISIONS.md` #1 rejected Supabase Auth for V1 specifically because it signs ES256 JWTs that a from-scratch HS256 verifier can't check — and that reasoning still holds for V2. Instead, §4.3–§4.4 above use plain bcrypt password hashing plus opaque bearer tokens verified against our own `session` table, which never touches JWT signing at all and sidesteps the ES256 problem entirely rather than solving it. The trade-off (XSS exposure of a `localStorage` token, no built-in email verification or password reset) is the one `docs/PRD-V2.md` §5 already accepts and defers to V3.
