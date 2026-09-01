# ANCHOR

Your degree isn't a single path — it's a position in a space of paths, and ANCHOR shows you where you're standing.

A CS student picks the courses they've taken and a few interests. One analysis returns the 8 roles they're closest to, ranked by a fit % computed from what their courses actually teach, plus 2–3 adjacent roles they hadn't considered. Ticking "I've learned this" on a missing skill re-ranks every role live, because all roles share one skill vocabulary.

## Docs

| | |
|---|---|
| `docs/PRD.md` | what we're building and why |
| `docs/TDD.md` | how it's built |
| `docs/CONTRACT.md` | every shape that crosses a lane boundary |
| `docs/DECISIONS.md` | one-line log of deviations |
| `docs/DEMO.md` | the 75-second runbook |
| `CLAUDE.md`, `.claude/skills/` | Claude Code project instructions and lane playbooks |

## Run

Nothing needs an account, a database server, or an API key to start — `.env.example` defaults
to SQLite, and the frontend runs against the committed fixtures.

```bash
# backend  -> http://localhost:8000  (docs at /docs, readiness at /health)
cd backend && cp .env.example .env   # SQLite by default; no key needed to boot
pip install -r requirements.txt
python scripts/seed_db.py            # creates dev.db and loads the 10 catalog courses
uvicorn app.main:app --reload --port 8000
pytest -q                            # 282 tests, no network calls

# frontend -> http://localhost:5173
cd frontend && cp .env.example .env  # VITE_USE_FIXTURE=true renders the committed fixtures
npm install && npm run dev
```

**To exercise the real model calls** (`POST /api/analyze`, `GET /api/project`, `POST /api/submit`)
set `GEMINI_API_KEY` in `backend/.env` — the provider is Google Gemini, see DECISIONS #39.
Everything else, including the whole roadmap and scoring path, runs without it.
`GITHUB_TOKEN` is only needed for `POST /api/submit` against a real repo.

Check a running instance end to end:

```bash
cd backend && python scripts/smoke_deploy.py --url http://localhost:8000
```

## Deploy

Two services: the API on **Render** (or Railway) and the frontend on **Vercel**.

> **Deploy the API from the repository ROOT — never with a root directory of `backend/`.**
> `contracts/fixtures/` sits outside `backend/`, and `app/analysis/demo.py` resolves it as
> `parents[3]`. A `backend/`-rooted deploy builds green, serves `/health` green, and then fails
> on the demo path in front of judges. `tests/test_deploy.py` pins this; `/health` reports it.

### API — Render

`render.yaml` is a blueprint: point Render at the repo and it reads the build command, start
command, health check and the env-var list. Railway users get the same start command from
`Procfile` / `nixpacks.toml`. Anything else: build `pip install -r backend/requirements.txt`,
start `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

Set these on the host (`render.yaml` marks the secrets `sync: false` so they are prompted, never committed):

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Supabase **session** pooler, port **5432** — the 6543 transaction pooler breaks prepared statements |
| `GEMINI_API_KEY` | without it `/analyze` 502s |
| `GITHUB_TOKEN` | unauthenticated GitHub is 60 req/h; judge trials exhaust it (DECISIONS #24) |
| `CORS_ORIGINS` | must include the Vercel origin, comma-separated |
| `DEMO_MODE` | `true` for the slot only |
| `DEMO_REPO_URL` | unset, the demo submit falls through to a **live** review: 4 s becomes up to 124 s |

The two new v4 tables mean **existing deployed tables must be dropped and recreated** —
`SQLModel.metadata.create_all` on startup, no migrations (TDD §10). Then run
`python scripts/seed_db.py` once against the deployed database.

### Frontend — Vercel

Root directory `frontend`, build `npm run build`, output `dist`, and set
`VITE_API_URL=https://<the-api-host>`. **Remove `VITE_USE_FIXTURE`** — left set, the deployed
frontend serves `contracts/fixtures/` and never calls the API.

### Verify it — one command

```bash
cd backend
python scripts/smoke_deploy.py --url https://<api-host> --origin https://<vercel-host>
```

Checks reachability, the database, that `contracts/fixtures/` actually shipped, every required
key, the catalog, CORS from the real frontend origin, and the identity 404. Exits non-zero on
any failure, so it can gate a pre-demo checklist.

### The Appendix B question

Live analysis measures **53-102 s**; TDD §5.1 warns some host proxies cut at ~100 s. Once
deployed, answer it with:

```bash
python scripts/smoke_deploy.py --url https://<api-host> --analyze
```

It creates one throwaway student (named `Smoke Test`, so `DEMO_MODE`'s cached path is bypassed),
times a real `/analyze`, and says whether the host cut the request. If it did, implement TDD
Appendix B (~40 lines in `routers/analyze.py`). If the pitch runs entirely in `DEMO_MODE` (6 s)
it never fires — a legitimate choice, but record it in `docs/DECISIONS.md` deliberately.


## Lanes

Salman — backend (`backend/app/**` except `analysis/`) · Umer — AI (`backend/app/analysis/**`) · Wahab — the entire frontend (Setup, Analyzing, Roadmap, drawer, animation).
See `CLAUDE.md` for the full ownership map and integration seams.

## v2 (not built)

Accounts · Courses page · syllabus upload · add courses over time · re-analyze preserving progress · live job-posting signal · cohort comparison · resource links per skill
