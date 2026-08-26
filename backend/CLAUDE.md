# backend/ — FastAPI service

Read `../docs/TDD.md` §4 before changing anything here. Contract shapes live in `../docs/CONTRACT.md`;
`app/schemas.py` is their Python mirror — if you change one, change the other in the same PR.

## Layout

- `app/main.py` — app factory, CORS, `create_all`, router mounting. Keep it under 40 lines.
- `app/config.py` — `Settings` via pydantic-settings. All env reads go through it.
- `app/db.py` — engine (`pool_pre_ping=True`) and `get_session`.
- `app/identity.py` — `current_student` dependency from the `X-Student-Id` header.
- `app/models.py` — SQLModel tables. **Shared file**; changes need a `contract:` PR.
- `app/schemas.py` — request/response models. **Shared file**.
- `app/scoring.py` — `fit_percent`. Pure. No imports from `app`. Mirrored in `frontend/src/lib/scoring.ts`.
- `app/persistence.py` — `persist_analysis`: AnalysisOut → rows, one transaction, no per-row flush.
- `app/github.py` — `fetch_repo(url) -> RepoBundle`. Token, 2 + ≤10 requests, 60 KB cap, `RepoError(user_message)`. No clone, no execution.
- `app/routers/` — one file per endpoint. `analyze.py`, `project.py`, `submit.py` are thin: they call `app.analysis.*` and write rows.
- `app/analysis/` — **Umer's lane.** Import `run_analysis` from it; do not edit it.

## Rules

- Every router except `courses.py` takes `student: Student = Depends(current_student)`.
  Scope every query by `student.id`. There is no other authorization.
- Never update or delete rows except `Progress`. Re-onboarding creates a new `Student`.
- `GET /api/roadmap` returns everything the UI needs in one payload, roles pre-sorted by `(-fit_percent, rank)`.
- `POST /api/progress` returns `{"ok": true}` only. Do not return recomputed fit.
- `Project` and `Submission` are append-only. `verified_skill_ids` on a submission is a copy of `project.verifies` when passed, else `[]`.
- Verified set = union over all passing submissions. Compute it in one query; return the full set from `/submit`.
- `fit_percent` uses `max(verified, tick, coverage)`. Read `docs/CONTRACT.md` §2 before touching it.
- Unknown `course_code` in coverage: log a warning and skip. Never fail the analysis for it.

## Run / test

```bash
uvicorn app.main:app --reload --port 8000
pytest -q                     # test_scoring, test_validation, test_parity
python scripts/seed_db.py     # idempotent: upserts the 10 catalog courses
python scripts/dump_roadmap.py --student <id> > ../contracts/fixtures/roadmap_response.json
```
