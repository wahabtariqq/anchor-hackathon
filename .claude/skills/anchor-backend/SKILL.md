---
name: anchor-backend
description: How to build and change the ANCHOR FastAPI backend — routers, SQLModel tables, the X-Student-Id identity dependency, persistence of an analysis into Postgres, roadmap assembly, and the progress endpoint. Use this for any task under backend/app/ (except backend/app/analysis/), for database or Supabase connection issues, for adding or changing an endpoint, for seed scripts, or when the user mentions FastAPI, SQLModel, Postgres, the roadmap payload, or fit % on the server.
---

# ANCHOR backend

Design reference: `docs/TDD.md` §4–§6 and §11. Contract: `docs/CONTRACT.md`. Read the
relevant TDD section before writing code; the snippets there are the intended implementation.

## Module map

| File | Contains | Touch it when |
|---|---|---|
| `app/main.py` | app, CORS, `create_all`, `include_router` × 5 | adding a router (rare) |
| `app/config.py` | `Settings` | adding an env var |
| `app/db.py` | engine with `pool_pre_ping=True`, `get_session` | never, really |
| `app/identity.py` | `current_student` | never |
| `app/models.py` | tables | **shared** — see anchor-contract |
| `app/schemas.py` | API models | **shared** — see anchor-contract |
| `app/scoring.py` | `fit_percent`, pure | only with the anchor-contract skill |
| `app/persistence.py` | `persist_analysis` | persistence bugs |
| `app/routers/*.py` | one endpoint each | endpoint work |
| `app/analysis/` | **not yours** | never — import `run_analysis` only |
| `seed/courses.py` | 10 catalog courses + curriculum text | curriculum edits |
| `scripts/` | `seed_db`, `dump_roadmap` | tooling |

## Rules that are easy to break

- Every router except `courses.py`: `student: Student = Depends(current_student)`. Scope
  all queries by `student.id`. Do not add other auth.
- `Progress` is the only table that is ever written after analysis. Never `UPDATE` or `DELETE`
  anything else. Re-onboarding creates a new `Student` row.
- Persistence builds the whole object graph in memory and commits once. Ids come from
  `default_factory`; there is no reason to `flush()` per row.
- `GET /roadmap` collapses coverage to the best depth per skill **before** calling
  `fit_percent`, sorts roles by `(-fit_percent, rank)`, and returns everything in one payload.
- `POST /progress` returns `{"ok": true}` and nothing else.
- Unknown `course_code` in coverage → `log.warning` and skip. Duplicate `(skill, course)` pair → skip.
- `analyze.py` stays thin: 409/422 checks, call `run_analysis` (or the demo loader), call
  `persist_analysis`, return. All model logic lives in `app/analysis/`.

## Working without the AI lane

Dev B's fixture `contracts/fixtures/demo_analysis.json` is a valid `AnalysisOut`. Load it with
`AnalysisOut.model_validate_json(...)` and feed it to `persist_analysis` in tests and while
building `GET /roadmap`. You never need to call Anthropic to work on this lane.

## Supabase / Postgres checklist

- Connection string is the **session pooler**, port `5432`, `postgresql+psycopg://`.
  The transaction pooler (6543) breaks prepared statements.
- `pool_pre_ping=True` or the app "dies" after a few idle minutes.
- `SQLModel.metadata.create_all(engine)` on startup. No migrations. If a column changes,
  drop the tables in the Supabase UI and restart.
- `Column(JSON)` for `Student.interests`. Import `Column, JSON` from `sqlalchemy`.

## Definition of done for an endpoint

1. Router file exists and is mounted in `main.py`.
2. Request/response models in `schemas.py` match `docs/CONTRACT.md` §3 exactly.
3. `pytest -q` green.
4. Curl it with a real `X-Student-Id` and paste the response into the PR.
5. If it's `/roadmap`: regenerate `contracts/fixtures/roadmap_response.json` via `scripts/dump_roadmap.py`.
