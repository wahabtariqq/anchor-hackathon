"""Engine and session dependency (docs/TDD.md §4.2).

Supabase: use the *session* pooler on port 5432. The transaction pooler (6543) does not
support prepared statements and SQLAlchemy fails in non-obvious ways. pool_pre_ping is not
optional — the pooler drops idle connections and without it the app "breaks" after a few
idle minutes.
"""

from collections.abc import Iterator
from typing import Any

from sqlmodel import Session, create_engine

from app.config import settings


def _engine_kwargs(url: str) -> dict[str, Any]:
    if url.startswith("postgres"):
        return {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}
    # SQLite (local run-throughs, tests) uses a pool class that rejects pool_size.
    return {"pool_pre_ping": True, "connect_args": {"check_same_thread": False}}


engine = create_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
