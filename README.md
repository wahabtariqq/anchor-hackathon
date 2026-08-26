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

```bash
# backend
cd backend && cp .env.example .env   # fill in DATABASE_URL, ANTHROPIC_API_KEY
pip install -r requirements.txt
python scripts/seed_db.py
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && cp .env.example .env  # VITE_USE_FIXTURE=true until Day 3
npm install && npm run dev
```

## Lanes

Dev A — backend + Setup screen · Dev B — AI pipeline (`backend/app/analysis/`) + Analyzing screen · Dev C — Roadmap, drawer, animation.
See `CLAUDE.md` for the full ownership map and integration seams.

## v2 (not built)

Accounts · Courses page · syllabus upload · add courses over time · re-analyze preserving progress · live job-posting signal · cohort comparison · resource links per skill
