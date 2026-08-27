# ANCHOR — project instructions for Claude Code

ANCHOR turns a CS student's course history + interests into 8 ranked career roles, shows
covered vs missing skills per role, and re-ranks every role live when the student ticks
"I've learned this". Hackathon build: 3 people, 3 days + buffer.

- Product truth: `docs/PRD.md` · Technical truth: `docs/TDD.md` · Shared contract: `docs/CONTRACT.md`
- If a request conflicts with PRD §2 non-goals (auth, upload, quizzes, courses page, mobile), say so and stop.

## Two invariants — never violate

1. **Skills are the only source of truth.** Courses and roles are views over the skill table.
   Progress is keyed to `skill.id`, never to a course or a role.
2. **Three model call types, then arithmetic.** Analysis (once per student), project generation (lazy,
   cached per student × role), repo review (per submission). Only `backend/app/analysis/` calls the model
   provider — **Gemini 2.5 Flash free tier, behind an `LLMClient` adapter; see DECISIONS #39.** Claude is
   the pinned fallback, not the default.
   Fit % and `passed` are computed in code (`scoring.py` / `scoring.ts`, `review.py`), never by the model.
3. **Nothing lowers a score.** Fit uses `max(verified, tick, coverage)`. Verified = union over all passing submissions.

## Repo map and ownership lanes

| Path | Owner | Notes |
|---|---|---|
| `backend/**` except `app/analysis/` | Salman | API, DB, persistence, scoring, `github.py`, `/project`, `/submit`, seed/scripts/tests |
| `backend/app/analysis/**`, `contracts/fixtures/demo_*.json` | Umer | Three model calls. Exposes `run_analysis`, `generate_project`, `review_repo`. Nobody else edits. |
| `frontend/**` | Wahab | The entire frontend — Setup, Analyzing, Roadmap/drawer/animation, state |
| `contracts/**`, `docs/CONTRACT.md`, `backend/app/schemas.py`, `frontend/src/lib/types.ts` | **shared** | Change only via a PR titled `contract: …` that updates every mirror at once, plus a chat ping |
| `frontend/src/components/ui/**` | shadcn CLI | generated, never hand-edit |

Before editing a file, check its lane. If it isn't yours, propose the change to the owner
instead of making it. Cross-lane work goes through the integration seams below.

## Integration seams (how three people work without blocking each other)

1. `backend/app/analysis/__init__.py` exports `run_analysis(student, courses) -> (AnalysisOut, raw_text)`.
   Salman's `routers/analyze.py` calls it; Umer never touches routers.
2. `contracts/fixtures/roadmap_response.json` is what `GET /api/roadmap` returns for the demo
   student. Wahab builds the entire UI against it with `VITE_USE_FIXTURE=true`. Salman regenerates
   it with `scripts/dump_roadmap.py` once the real endpoint works. When the real response has the
   same shape, integration is done.
3. `contracts/fixtures/demo_analysis.json` is Umer's validated model output. It feeds both
   `DEMO_MODE` and Salman's persistence tests.
4. `contracts/fixtures/parity_cases.json` is read by both `test_parity.py` and `scoring.test.ts`.
5. `app.github.fetch_repo(url) -> RepoBundle` (Salman) feeds `app.analysis.review_repo(project, bundle)` (Umer).
   Prove It is Day 3 afternoon + Day 4 and only starts once the core is deployed (PRD §13).

## Commands

```bash
# backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest -q
python scripts/seed_db.py
python scripts/run_analysis_cli.py --demo          # Umer: pipeline only, no DB, saves fixture
python scripts/dump_roadmap.py --student <id>      # Salman: refresh roadmap_response.json
python -m app.analysis.export_schema               # Umer: refresh contracts/analysis.schema.json
python scripts/run_project_cli.py --role data-engineer        # Umer: project from demo_analysis.json
python scripts/run_review_cli.py --url https://github.com/o/r # Umer: fetch + review against demo_project.json

# frontend
cd frontend && npm install
npm run dev                                        # http://localhost:5173
npm test                                           # vitest, includes scoring parity
npx shadcn@latest add <component>
```

## Conventions

- Python 3.12, FastAPI, SQLModel, Pydantic v2. Type hints everywhere. No Alembic.
- TypeScript strict. React function components + hooks. Tailwind + shadcn only. No Redux, no React Query.
- No `localStorage` anywhere except `frontend/src/lib/identity.ts`.
- No new endpoints, tables, pages, or npm packages without a note in `docs/DECISIONS.md`.
- Commit messages: `lane(scope): what` — e.g. `ai(prompt): tighten dedup instruction`, `api(roadmap): collapse coverage depth`, `ui(roadmap): translateY re-sort`.
- Every skill in `.claude/skills/` describes when to use it. Read the matching one before starting a task in that lane.
