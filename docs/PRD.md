# ANCHOR — Product Requirements Document (v3)

**Hackathon build · 3 people · 3 days + 1 buffer day**
**Stack:** FastAPI + React (Vite) + Postgres (Supabase)
**Status:** Locked. Anything not in this document is out of scope.

*Changes from v2: auth removed · role detail is a drawer on the Roadmap (so the re-sort is actually visible) · Courses page cut · "what moved" delta added · structured outputs · demo cache gated to the demo student · team load rebalanced.*

---

## 1. Product summary

A CS student enters the major courses they've taken and picks a few interest areas. ANCHOR runs one analysis and returns the **8 career roles they're closest to**, ranked by fit %, including 2–3 deliberately adjacent roles they hadn't considered. Opening a role shows which required skills their coursework already covers and which are missing, priority-ordered, each with a real-world framing. Ticking a missing skill recomputes **every role at once** — and the ranking visibly reorders on screen.

**The one-sentence pitch:** *Your degree isn't a single path — it's a position in a space of paths, and ANCHOR shows you where you're standing.*

---

## 2. Goals & non-goals

### Goals

| # | Goal | How it's judged |
|---|---|---|
| G1 | Turn raw course history into a ranked set of realistic roles | 8 roles, ordered by fit %, ranking is defensible |
| G2 | Make the gap concrete and actionable | Every role shows covered vs missing skills with real-world context |
| G3 | Show the student they can move | One checkbox visibly reorders the ranking, on the same screen, in under 100ms |
| G4 | Stay explainable in 60 seconds | One input screen, one analysis, one results screen |

### Non-goals (explicitly out of scope)

- **Authentication of any kind** — no signup, login, email, password, OAuth (see §5)
- Quizzes, tests, or assessments
- Adding or editing courses after the analysis
- **File upload of any kind** — PDF, DOCX, textbook parsing (paste only, see §6.1)
- Live job-market scraping
- A separate Courses page (moved to v2, see §15)
- Mobile layout — desktop only, demo laptop resolution
- Error handling beyond one retry + a friendly failure screen
- Multi-user, sharing, export, notifications

> **Rule for the team:** if a feature isn't in §10 Screens, it does not get built. Put it in the README's v2 section instead.

---

## 3. The core architectural rule

**Skills are the single source of truth.**

- A **skill** is an atomic, named capability with a stable `slug`.
- A **course** is a view: the set of skills that course covers.
- A **role** is a view: a weighted subset of skills that role requires.
- **Progress** is stored against skill ids — never against courses or roles.

This is why one checkbox moves several roles simultaneously. Decide this on Day 1 and enforce it in code review.

---

## 4. Architecture

### 4.1 Pipeline count: one

There is exactly **one** call to the model in the entire product, at analysis time, once per student.

```
[selected courses + curriculum text] + [interest tags]
                    │
                    ▼
        ┌───────────────────────┐
        │   ANALYSIS CALL       │   ← the only AI in the product
        │   Claude, structured  │
        │   JSON output,        │
        │   validated by        │
        │   Pydantic            │
        └───────────────────────┘
                    │
                    ▼
   skills[]  +  roles[]  +  coverage[]
                    │
                    ▼
   written to Postgres, immutable
                    │
                    ▼
   Everything after this is arithmetic.
```

### 4.2 What never calls the model

Checking a skill · loading the Roadmap · opening a role · recomputing any fit %.

Fit % is computed in code on every read. Deterministic, instant, identical across page loads.

### 4.3 Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | **FastAPI** + SQLModel + Pydantic v2 | Pydantic is the validation layer |
| DB | **Postgres** (Supabase, session pooler) | Direct SQLAlchemy connection. Any hosted Postgres works; Railway/Render's add-on is fine too |
| Identity | **None.** Backend mints a student id; browser keeps it in `localStorage` | See §5 |
| Frontend | **React + Vite** + Tailwind + shadcn/ui | Card, Progress, Checkbox, Badge, Sheet (drawer) come ready-made |
| AI | `anthropic` Python SDK, structured outputs | Server-side only, key in backend env |
| Deploy | Railway/Render (API) + Vercel (frontend) | Deploy hello-world of both on **Day 1** |

Do not introduce Redux or React Query. One context + `fetch` is enough.

### 4.4 Supabase: database only

If using Supabase, use it as a Postgres host and nothing else. No `supabase-js`, no RLS, no Auth. The API is the only thing touching the tables. Use the **Session pooler** URI (port 5432); the transaction pooler breaks SQLAlchemy prepared statements.

---

## 5. Identity (there is no auth)

Auth earns zero judge points, and the v2 design would have cost most of Day 1: new Supabase projects sign JWTs with asymmetric ES256 keys, so the HS256 verification in v2 would have returned 401 on a fresh project. We're removing the whole category of risk.

**How identity works instead:**

1. Setup screen collects name + semester + courses + interests.
2. `POST /api/students` creates the student and returns `{ student_id }` (a UUID).
3. Frontend stores it in `localStorage` and sends it as `X-Student-Id` on every request.
4. On load, if a stored id exists and `GET /api/roadmap` returns 200 → go to Roadmap. Otherwise → Setup.
5. A small **"Start over"** link in the header clears the id and returns to Setup.

Re-onboarding always creates a *new* student. Nothing is ever updated or deleted, which removes an entire class of cascade bugs.

**Judge question:** *"Where's login?"* → "We spent that day on the analysis quality instead. Identity is a v2 line item; the data model already keys everything to a student id."

---

## 6. Course input

### 6.1 Three paths, one field

Every path writes a curriculum string into the same column. **No upload, no parsing.**

| Path | How | Effort |
|---|---|---|
| **A. Catalog (primary)** | Pick from 10 pre-seeded CS courses with built-in curriculum text | Built-in |
| **B. Override** | On any selected card: *"My syllabus is different — paste it"* → textarea | ~30 min |
| **C. Custom course** | *"+ Add a course not listed"* → name + pasted outline | ~15 min |

Demo uses Path A. Mention B and C in one sentence.

### 6.2 Seed catalog

Each needs 120–200 words of realistic curriculum text (a topic list from any real CS syllabus is fine).

| Code | Name |
|---|---|
| CS201 | Data Structures & Algorithms |
| CS202 | Object-Oriented Programming |
| CS301 | Database Management Systems |
| CS302 | Operating Systems |
| CS303 | Computer Networks |
| CS401 | Machine Learning |
| CS402 | Web Development |
| CS403 | Software Engineering |
| CS404 | Probability & Statistics |
| CS405 | Computer Vision |

### 6.3 Interest tags

Fixed list of 8, multi-select, minimum 2: `Artificial Intelligence`, `Databases`, `UI/UX Design`, `Web Development`, `Systems & Infrastructure`, `Data Analysis`, `Security`, `Mobile`.

---

## 7. Data model

See TDD §4 for the SQLModel definitions. Tables:

- `student` — id (UUID), name, semester, interests (JSON)
- `course` — pre-seeded catalog, read-only at runtime
- `studentcourse` — the student's selection, with resolved `curriculum_text` and an always-populated `code` (`CS301` or `CUSTOM-1`)
- `analysis` — one per student, holds the raw model output for debugging
- `skill` — the shared vocabulary for one analysis (`slug` unique per analysis)
- `role` — 8 per analysis, `proximity` core/adjacent, `bridge` text, model `rank` (tiebreaker only)
- `roleskill` — (role, skill, weight core/supporting)
- `coverage` — (skill, studentcourse, depth full/partial)
- `progress` — (student, skill) rows; the only table that changes after analysis

---

## 8. The analysis call

### 8.1 Request

- Model: `claude-sonnet-4-6`
- `max_tokens`: 16000 (retry at 24000 if the response stops on `max_tokens`)
- `temperature`: 0.3
- **Structured outputs** (`output_config.format` with the JSON schema derived from the Pydantic model) — guarantees parseable JSON. No fence-stripping, no prefill (prefill is unsupported on 4.6+ and incompatible with structured outputs anyway).
- Backend only: `POST /api/analyze`

### 8.2 Output schema

```jsonc
{
  "skills": [
    {
      "id": "sql-query-optimization",       // kebab-case, unique within the response
      "name": "SQL Query Optimization",
      "real_world": "Cutting a 4-second dashboard query to 40ms is usually one missing composite index."
    }
    // 40–60 total
  ],
  "coverage": [
    { "skill_id": "sql-query-optimization", "course_code": "CS301", "depth": "full" }
    // depth: "full" | "partial"
  ],
  "roles": [
    {
      "id": "data-engineer",
      "title": "Data Engineer",
      "one_liner": "Builds the pipelines that move and reshape data for analysts and models.",
      "proximity": "core",                   // "core" | "adjacent"
      "bridge": "",                          // empty for core; required sentence for adjacent
      "rank": 1,
      "skills": [
        { "skill_id": "sql-query-optimization", "weight": "core" },
        { "skill_id": "python-scripting", "weight": "supporting" }
        // 10–14 per role, no skill repeated within a role
      ]
    }
    // exactly 8 roles
  ]
}
```

`bridge` is a plain string (empty for core roles) rather than nullable, because union types are the most expensive thing in a structured-output grammar and we don't need one.

### 8.3 Prompt

```
You are a CS curriculum and career analyst. You will be given a university
student's completed and in-progress major courses (with curriculum detail)
and their stated interest areas. Produce a structured analysis of the career
paths they are currently closest to.

STUDENT
Semester: {semester}
Interests: {interests}

COURSES
{for each course: CODE — NAME
CURRICULUM: {curriculum_text}}

TASK
Return a JSON object with three top-level keys: "skills", "coverage", "roles".

1. SKILLS — a flat, deduplicated vocabulary of 40 to 60 atomic skills spanning
   every role you will produce. Each skill gets a kebab-case "id", a human
   "name", and a "real_world" sentence naming a concrete situation where the
   skill decides an outcome. Be specific; avoid generic filler.

   CRITICAL: this list is a shared vocabulary. One concept appears exactly
   once. Do not emit "SQL", "SQL Querying" and "Relational Databases" as
   separate skills — pick one id and reuse it across every role that needs it.
   Skills must be atomic capabilities, not course names or job titles.

2. COVERAGE — which skills the student's listed courses already teach. Use
   "full" when the curriculum clearly covers it, "partial" when it introduces
   the skill without depth. Only reference course codes from the list above.
   Do not force coverage that isn't in the curriculum text.

3. ROLES — exactly 8 realistic, current CS industry roles, each built ONLY
   from skill ids that exist in "skills".
   - 5 or 6 must have proximity "core": directly aligned with the student's
     coursework and interests. Their "bridge" is the empty string.
   - 2 or 3 must have proximity "adjacent": genuinely reachable but outside
     what the student would have guessed. Each adjacent role MUST have a
     "bridge" sentence naming the specific coursework or interest that
     connects them to it, phrased directly to the student ("Your …").
   - Each role lists 10 to 14 distinct skills, each weighted "core"
     (essential) or "supporting" (expected, learnable on the job).
   - Rank roles 1..8 by your judgement of overall fit.
   - Roles should sit within a coherent family — do not pad with unrelated
     titles to reach 8.
```

### 8.4 Validation

Structured outputs guarantee the *shape*. Pydantic validators still enforce the *semantics* the grammar can't:

- skill ids unique
- every `skill_id` in roles and coverage exists in `skills`
- no skill repeated within one role
- exactly 8 roles, 5–6 core
- adjacent roles have a non-empty bridge

Unknown `course_code` in coverage → **drop with a warning**, not fatal.

**Retry policy:** on validation failure or `stop_reason == "max_tokens"`, retry once (with a higher token limit in the second case). On second failure → 502 → error screen with **Try again**. Persist inside one DB transaction; once written, the analysis is immutable.

---

## 9. Fit % formula

Computed in code on every read. Never from the model.

```
WEIGHT = { core: 3, supporting: 1 }
DEPTH  = { full: 1.0, partial: 0.5 }

for each skill the role requires:
    total  += WEIGHT[weight]
    earned += WEIGHT[weight]                     if student ticked "I've learned this"
           |= WEIGHT[weight] * DEPTH[best depth] else if any course covers it
fit = round_half_up(earned / total * 100)     # Python int(x + 0.5), TS Math.round
```

- A ticked skill always beats partial coursework coverage — that's what makes the checkbox feel like progress.
- Ranking: fit % desc, then model `rank` asc as tiebreaker.
- Roles below **15%** still display, labelled *"Not enough foundation yet."*
- **Mirror this function in TypeScript** for instant client-side recompute. Both implementations are tested against one shared fixture (TDD §8).

**Judge question:** *"Can't I just tick everything and hit 100%?"* → "Yes — it's a self-assessment, labelled 'I've learned this'. The coursework coverage is model-derived and read-only; the checkbox is the student telling us what they've done since. The point isn't to gate them, it's to show them how the landscape shifts as they learn."

---

## 10. Screens

Three. No more.

### 10.1 Setup — `/setup`

- Name, semester number
- **Courses:** 10 catalog cards, toggleable, grouped `Previous semesters` / `Current semester`. Min 3, max 6.
  - Each selected card shows *"My syllabus is different — paste it"* → inline textarea
  - Below the grid: **+ Add a course not listed** → name + outline textarea
- **Interests:** 8 chips, min 2
- Primary button: **Analyze my path** (disabled until minimums met)

### 10.2 Analyzing — `/analyzing`

The call is slow. This screen is load-bearing, not a spinner.

- Staged copy on a timer, decoupled from the request:
  `Reading your course curricula…` → `Extracting skill coverage…` → `Mapping career paths…` → `Ranking roles by fit…`
- Indeterminate progress bar
- Redirect to `/roadmap` on completion; on failure show **Try again**

### 10.3 Roadmap — `/roadmap` *(the money screen)*

Two-column desktop layout. **Left: the ranking. Right: the role drawer.** Both visible at once — that is the whole point.

**Header:** name, semester, course count, interest chips, "Start over" link.

**Left column, Section A — "Your closest paths"** (`core`, 5–6 cards, fit % desc)
- Role title + one-liner
- Large fit % with progress ring
- `X of Y skills covered`
- Top 2 missing core skills as red-tinted badges
- Click → opens the role in the right drawer (URL updates to `/roadmap?role=slug` so it's linkable)

**Left column, Section B — "Worth considering"** (`adjacent`, 2–3 cards, dashed border, lighter background)
- Same, plus the **bridge line** in italic:
  > *"Your UI/UX interest and DBMS coursework converge here — you're 2 skills from a full-stack path."*

**Right drawer — role detail** (shadcn `Sheet`, or a fixed right panel)
- Header: title, one-liner, fit ring, bridge if adjacent
- **Missing skills** first, core weight before supporting: checkbox labelled *"I've learned this"* · name · `core`/`supporting` badge · real-world sentence beneath
- **Already covered by your courses**, collapsed by default: name · course code badge · `partial` marker
- Ticking a box: local state updates synchronously; the drawer's ring animates **and the left column re-sorts with a CSS transition, at the same moment.** POST happens in the background.

**"What moved" strip** — after any tick, a small line under Section A summarises the biggest change, e.g. *"Data Engineer 48% → 71% · moved #4 → #2"*. Fades after 4s. This is so a judge who blinked still sees what happened.

**Live-update requirement:** any checkbox change recomputes every card and re-sorts Section A with a visible slide transition. This animation is the demo. Budget real time for it, on Day 2, not Day 3.

---

## 11. API surface

Five endpoints. All except `/api/courses` require `X-Student-Id`.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/courses` | Catalog for the setup screen (public) |
| `POST` | `/api/students` | Create student + course selections + interests → `{ student_id }` |
| `POST` | `/api/analyze` | The one AI call. Validates, persists, returns `{ ok: true }` |
| `GET` | `/api/roadmap` | Roles + computed fit % + coverage + checked skills, one payload |
| `POST` | `/api/progress` | `{ skill_id, checked }` — insert or delete a `progress` row |

`/api/roadmap` returns everything the Roadmap and drawer need. Fetch once, hold in context, recompute fit % client-side on every tick. Persist in the background.

**CORS:** configure the Vercel origin plus `http://localhost:5173` on Day 1.

---

## 12. Demo safety

### 12.1 Cached payload — gated to the demo student

Run the analysis once for the demo student on Day 2. Save the validated JSON to `backend/seed/demo_analysis.json`. When `DEMO_MODE=true` **and the student's name matches `DEMO_STUDENT_NAME`**, `/api/analyze` sleeps 6 seconds and loads the cached payload. Everyone else gets a real call.

Why gated: judges can try it themselves with their own courses after the pitch, live, and it still works. That's a much stronger close than "the demo account is special".

### 12.2 Canonical demo student

| Field | Value |
|---|---|
| Name | Ayesha · Semester 4 |
| Past courses | CS201 Data Structures & Algorithms, CS301 Database Management Systems |
| Current courses | CS401 Machine Learning, CS402 Web Development |
| Interests | Artificial Intelligence, Databases, UI/UX Design |

Chosen deliberately: inputs span three umbrellas, so the ranking looks intelligent rather than obvious, and a full-stack / product role surfaces as a credible adjacent.

**Before the slot:** open the deployed URL on the demo laptop, run through Setup once, confirm the Roadmap renders, then hit "Start over" so the Setup screen is pre-filled and ready.

### 12.3 Demo script (60 seconds)

1. **0:00** — Setup screen. Four courses, three interests. *"A 4th-semester student. Two courses done, two in progress."*
2. **0:08** — *(3s)* Point at the paste link: *"Different syllabus? Paste your own."*
3. **0:11** — Analyze. Analyzing screen runs (6s in demo mode).
4. **0:18** — Roadmap. *"Eight roles, ranked by how far along she already is. Not a quiz — computed from what her courses actually teach."*
5. **0:28** — Adjacent section. Read one bridge line aloud. *"She never asked for this one — the system found it."*
6. **0:38** — Click a role. Drawer opens. *"Covered by her coursework. Missing. Each with where it actually matters."*
7. **0:46** — Tick three boxes. **Left column reorders while you're still talking.** *"Every role recomputes at once, because they all share one skill vocabulary."* Point at the "what moved" line.
8. **0:57** — Stop talking.

Assign now: who clicks, who talks. Rehearse until it's comfortably under a minute.

---

## 13. Three-day plan (+ buffer)

**Dev A — Backend, DB, deploy, Setup screen · Dev B — AI pipeline, Analyzing screen, demo payload · Dev C — Roadmap, drawer, animation**

The frontend is split across two people this time; v2 gave Dev C nearly everything visible and Dev A a light backend.

### Day 1 — Foundations

| Who | Work |
|---|---|
| **All (first 60 min)** | Agree the JSON contract (§8.2) and the SQLModel schema (TDD §4). Commit both before splitting. |
| **All (next 30 min)** | Deploy hello-world FastAPI and hello-world Vite. Confirm a cross-origin `GET` works from the deployed frontend. |
| A | Postgres, `DATABASE_URL`, tables, seed 10 courses, `X-Student-Id` dependency, `GET /courses`, `POST /students` |
| B | `/api/analyze` with structured outputs, Pydantic models + validators, prompt v1 — **one validated response saved to a fixture file by end of day**, and **the real wall-clock latency written down** |
| C | Vite + Tailwind + shadcn, app shell, context, `scoring.ts`, `FitRing`, `RoleCard` rendering B's fixture |

**Exit criteria:** B has a validated fixture on disk and a measured latency. C renders static cards from it. A's API returns the catalog on the deployed URL.

> If B has no valid response by end of Day 1, everyone stops and fixes the prompt together.

### Day 2 — The engine and the moment

| Who | Work |
|---|---|
| A | Persist transaction, `fit_percent` + tests, `GET /roadmap`, `POST /progress`. Then: **Setup screen** against `/api/courses`, incl. paste override and custom course |
| B | Retry logic, course-code cross-check, prompt tuning (skill dedup first, then adjacent-role interestingness, then real_world specificity). Generate + commit `demo_analysis.json`. `DEMO_MODE` branch. |
| C | **Roadmap two-column layout, drawer, checkbox flow, transform-based re-sort animation, "what moved" strip.** All against the fixture. This is the demo — it gets the full day. |

**Exit criteria:** Ticking a box in the drawer visibly re-sorts the left column. Python and TS fit functions agree on the parity fixture. Setup screen posts a real student.

### Day 3 — Integration and freeze

| Who | Work |
|---|---|
| A + C | Wire Setup → Analyzing → Roadmap against the real API. Delete the fixture path. |
| B | Analyzing screen with staged copy, client timeout, error screen with Try again |
| A | Optimistic revert path for `/progress`, "Start over", empty/loading states |
| All (last 2h) | Deploy both. Run the demo on the deployed URLs on the demo laptop, twice. |

**Exit criteria — HARD FREEZE at end of day.** Every feature in §10 works on the deployed URLs. No new features after this, by anyone, for any reason.

### Day 4 — Polish, rehearse, ship *(if you have it)*

| Time | Work |
|---|---|
| Morning | Visual pass: spacing, typography, ring, re-sort easing. |
| Midday | Run the full demo on the deployed URLs three more times. |
| Afternoon | Rehearse the 60-second script. README with the v2 section. |
| Last 2 hours | **Buffer. Something will break.** |

**If you only get 3 days:** Day 3's last two hours become rehearsal, the visual pass is whatever C has already done, and the README is written the night before. The product is the same.

**Day 4 rule:** if a bug can't be fixed in 30 minutes, hide the feature.

---

## 14. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Model emits duplicate/near-duplicate skills, breaking cross-role linkage | **High** | Prompt dedup instruction; Day-2 tuning targets this first; eyeball the fixture manually |
| Analysis latency far longer than expected (~10k output tokens) | **High** | Measure Day 1; 240s client timeout; check host request timeout; `DEMO_MODE` for the slot |
| Scope creep (quizzes, upload, courses page, auth) | **High** | §2 non-goals; Day 3 hard freeze |
| Re-sort animation built last, feels janky | Medium | Built Day 2 by a dedicated person, against a fixture, before any integration |
| Two-service deploy/CORS failure late | Medium | Both hello-worlds deployed Day 1, hour 2 |
| Supabase pooler + SQLAlchemy connection issues | Medium | Session pooler (5432), `pool_pre_ping=True` |
| Output truncated at `max_tokens` | Medium | 16k limit, retry at 24k on `stop_reason == "max_tokens"` |
| Structured-output schema rejected as too complex | Low | Schema is flat, all fields required, one enum-free string for bridge; if a 400 ever appears, drop `pattern` and let Pydantic check it post-hoc |

---

## 15. Anticipated judge questions

**"What if my university's syllabus is different?"**
Paste it. Any selected course can be overridden with your own outline, and you can add courses that aren't in our catalog. The analysis runs on whatever text you give it.

**"Won't these role requirements go stale?"**
Roles are generated per student at analysis time, not maintained in a static file, so they refresh as the model does. Live job-market signal is the natural v2.

**"How do you know the fit % is accurate?"**
It isn't a model output — it's arithmetic over a weighted skill set: core skills count triple, partial coursework counts half. Deterministic and identical on every load. The model identifies skills and roles; the scoring is ours.

**"Why did one checkbox change four cards?"**
All 8 roles are built from one shared skill vocabulary emitted in one call. `sql-query-optimization` is the same row for every role that needs it, so progress propagates structurally, not through syncing logic.

**"Can't I just tick everything?"**
See §9. It's a self-assessment; coursework coverage is the model's, the checkbox is the student's.

**"Where's login?"**
See §5. Deliberately cut; identity is one line in the data model already.

**"What was the hardest part?"**
Skill vocabulary consistency. If the model emits one concept under three names, cross-role progress silently breaks. Hence one call, an explicit dedup constraint, and validators that hard-fail on any role referencing an unknown skill id.

---

## 16. v2 (README only — do not build)

- Accounts (Supabase Auth with ES256 JWKS verification — see TDD Appendix A)
- Courses page: same skills, filtered per course, same progress rows
- File upload (DOCX/PDF syllabus) writing into the same curriculum field
- Add courses over time, mapped onto the existing frozen skill vocabulary
- "Re-analyze my path" — regenerate roles while preserving ticked skill ids
- Live job-posting signals as a display-only trending strip
- Peer comparison across a cohort
- Curated resource links per missing skill
