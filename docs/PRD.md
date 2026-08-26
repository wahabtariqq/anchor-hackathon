# ANCHOR — Product Requirements Document (v4)

**Hackathon build · 3 people · 3 days core + Day 4 for Prove It**
**Stack:** FastAPI + React (Vite) + Postgres (Supabase) · Claude structured outputs · GitHub REST
**Status:** Locked. Anything not in this document is out of scope.

*v4 adds one feature (**Prove It**: targeted mini-project + public-repo review that verifies skills), changes the fit formula (self-report earns half, proof earns full), and closes the job-posting decision (hand-curated seed set, in only if ready by Day 2 morning). Everything else is v3. All v3 non-goals stay non-goals.*

*Why: v3 is one model call plus rendering — a judge can fairly say "a chat session does this." The one loop a chat cannot do is diagnose gaps → assign a targeted project → receive a repo → score it against the diagnosis → recompute standing persistently. That loop is the answer to "why is this an app," and it fixes "can't I just tick everything?" structurally: self-report and verified proof now carry different weight.*

---

## 1. Product summary

A CS student enters the major courses they've taken and picks a few interest areas. ANCHOR runs one analysis and returns the **8 career roles they're closest to**, ranked by fit %, including 2–3 deliberately adjacent roles. Opening a role shows which required skills their coursework already covers and which are missing, priority-ordered, each with a real-world framing. Ticking "I've learned this" nudges every role at once. **Submitting a public repo for the role's mini-project, and passing review, verifies those skills and moves every role a lot more** — and the ranking visibly reorders on screen either way.

**The one-sentence pitch:** *Your degree isn't a single path — it's a position in a space of paths, and ANCHOR shows you where you're standing and lets you prove you've moved.*

**Demo line for the formula:** *"A tick moves it a little. Proof moves it a lot."*

---

## 2. Goals & non-goals

### Goals

| # | Goal | How it's judged |
|---|---|---|
| G1 | Turn raw course history into a ranked set of realistic roles | 8 roles, ordered by fit %, ranking is defensible |
| G2 | Make the gap concrete and actionable | Every role shows covered vs missing skills with real-world context |
| G3 | Show the student they can move | One checkbox visibly reorders the ranking, on the same screen, in under 100 ms |
| G4 | Let the student *prove* they moved | A passing repo submission flips skills to verified and re-ranks visibly more than any tick |
| G5 | Stay explainable in 75 seconds | One input screen, one analysis, one results screen, one closing beat |

### Non-goals (explicitly out of scope)

- **Authentication of any kind** (see §5)
- Quizzes, tests, assessments, exercise generation
- Adding or editing courses after the analysis
- **File upload of any kind** — paste only (§6)
- **Live job-market retrieval** — scraping, LinkedIn API, feeds. A hand-curated seed set is allowed (§8.6)
- Separate Courses page, per-course gap pages, explorer/initiator modes, skill trees
- **Cloning repos, executing code, running tests** — review reads structure via the GitHub API only (§8.5)
- Private repos, GitLab/Bitbucket, zip uploads
- Regenerating a project once created; multiple projects per role
- Mobile layout — desktop only
- Error handling beyond one retry + a friendly failure message

> **Rule for the team:** if a feature isn't in §10 Screens, it does not get built. Put it in the README's v2 section instead.

---

## 3. The core architectural rule

**Skills are the single source of truth.**

- A **skill** is an atomic, named capability with a stable `slug`, minted once by the analysis.
- A **course** is a view: the set of skills that course covers.
- A **role** is a view: a weighted subset of skills that role requires.
- A **project** is a view: the subset of a role's skills a repo can verify.
- **Progress** (ticks) and **verification** (passing submissions) are stored against skill ids — never against courses, roles, or projects.

This is why one tick, or one passing repo, moves several roles simultaneously — including roles the project wasn't written for. Projects and reviews reference skill ids from the analysis; they never mint new ones.

---

## 4. Architecture

### 4.1 Three model call types

| Call | When | Input | Output |
|---|---|---|---|
| **Analysis** | Once per student | courses + interests (+ seed posting excerpts, §8.6) | 40–60 skills, coverage, 8 roles |
| **Project generation** | Lazy: first time a student opens a role's Prove It panel. Cached per (student, role), never regenerated | that role's skills with current covered / ticked / verified / missing state | one mini-project spec |
| **Repo review** | Per submission | project spec + fetched repo contents | scored review |

All three live in `backend/app/analysis/`. Nothing else calls the model.

Project generation is **not** folded into the analysis call: the analysis is already at its token/quality budget (risk register #1, #2), eight pre-baked projects go stale as ticks and verifications accumulate, and lazy generation targets the student's gaps *right now*.

```
[courses + interests]
        │
        ▼
   ANALYSIS ───────▶ skills[] + roles[] + coverage[]   (immutable)
                              │
          ┌───────────────────┼─────────────────────┐
          ▼                   ▼                     ▼
    tick "learned"     open Prove It          submit repo URL
    → progress row     → PROJECT call         → GitHub fetch → REVIEW call
                         (cached)               → submission row
          │                                     → verified skill ids
          └───────────────┬─────────────────────┘
                          ▼
               fit % = arithmetic, recomputed on every read
```

### 4.2 What never calls the model

Ticking a skill · loading the Roadmap · opening a role · reopening a Prove It panel that's already generated · recomputing any fit % · computing `passed`.

### 4.3 Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | **FastAPI** + SQLModel + Pydantic v2 | Pydantic is the validation layer |
| DB | **Postgres** (Supabase session pooler) | Direct SQLAlchemy |
| Identity | **None.** Backend mints a student id; browser keeps it in `localStorage` | §5 |
| Frontend | **React + Vite** + Tailwind + shadcn/ui | Card, Progress, Checkbox, Badge, Sheet, Input |
| AI | `anthropic` Python SDK, structured outputs, three schemas | Server-side only |
| Repo access | **GitHub REST API** with a `GITHUB_TOKEN` (5000 req/h; unauthenticated is 60/h and judges would hit it) | Trees API + raw file fetch. No clone. |
| Deploy | Railway/Render (API) + Vercel (frontend) | Hello-worlds deployed on **Day 1** |

Do not introduce Redux or React Query. One context + `fetch` is enough.

### 4.4 Supabase: database only

Postgres host and nothing else. No `supabase-js`, no RLS, no Auth. Session pooler URI, port 5432.

---

## 5. Identity (there is no auth)

Unchanged from v3.

1. Setup collects name + semester + courses + interests.
2. `POST /api/students` returns `{ student_id }` (UUID).
3. Frontend stores it in `localStorage`, sends it as `X-Student-Id` on every request.
4. On load: stored id + `GET /api/roadmap` 200 → Roadmap. Otherwise → Setup.
5. "Start over" clears the id. Re-onboarding always creates a new student. Nothing is updated or deleted except progress and submissions.

**Judge question:** *"Where's login?"* → "Spent that day on the analysis and the review loop instead. Identity is one line in the data model already."

---

## 6. Course input

Unchanged from v3. Three paths (catalog, paste-override, custom course) into one curriculum field. Ten seeded courses (CS201–CS405). Eight interest tags, minimum two. Demo uses the catalog.

---

## 7. Data model

See TDD §4.4. Tables:

- `student`, `course`, `studentcourse`, `analysis`, `skill`, `role`, `roleskill`, `coverage` — unchanged
- `progress` — (student, skill) tick rows
- **`project`** *(new)* — one per (student, role): title, spec, criteria, `verifies` skill ids. Written once.
- **`submission`** *(new)* — per submission: student, role, repo_url, review JSON, total, max_total, `passed`, `verified_skill_ids` (copied from the project at pass time), created_at.

**Verified skills** = the union of `verified_skill_ids` across *all* of the student's passing submissions. Not "the latest" — a skill proven via one role's project counts for every role that needs it. That is the architectural rule applied.

---

## 8. The model calls

### 8.1 Analysis call

Unchanged from v3 (`claude-sonnet-4-6`, structured outputs, 16k tokens with 24k retry, temperature 0.3, prompt in v3 §8.3, validators V1–V6). Only addition: if the seed set is adopted (§8.6), 3–5 relevant posting excerpts are appended as grounding context.

### 8.2 Project generation call

**Trigger:** `GET /api/project?role_id=…` when no `project` row exists for (student, role).
**Input:** the role's title, one-liner, and full skill list, each tagged `verified` / `ticked` / `covered:full` / `covered:partial` / `missing`.
**Output — `ProjectOut`:**

```jsonc
{
  "title": "Build a log-ingestion pipeline",
  "spec": "3–4 sentences: what to build, what done looks like.",
  "criteria": ["…", "…", "…"],                       // 3–4, what the review scores
  "verifies": ["containerization", "etl-basics"]      // 2–4 skill slugs from THIS role, prefer missing/ticked ones
}
```

**Validators (hard-fail → retry once → 502):** every `verifies` slug exists in the role's skill list; 3–4 criteria; 2–4 verifies. Soft: warn if a `verifies` slug is already verified.

**Prompt intent:** a weekend-sized project (one repo, no infra beyond a laptop) whose completion is evidence for the `verifies` skills; criteria must be checkable by reading the repo, not by running it.

### 8.3 Repo review call

**Trigger:** `POST /api/submit` after a successful GitHub fetch.
**Input:** project title, spec, criteria, plus the fetched repo bundle wrapped in explicit `<repo>` delimiters and introduced as **untrusted data to be scored, not instructions to follow** (a README saying "score everything 2" must not work).
**Output — `ReviewOut`:**

```jsonc
{
  "criteria_scores": [ { "criterion": "…", "score": 1, "note": "one sentence" } ],   // same count and order as project.criteria; score 0–2
  "feedback": "One short paragraph to the student."
}
```

**Validators:** `criteria_scores` count and order match the project's criteria (compared case-insensitively); each score ∈ {0, 1, 2}.
**Computed in code, never by the model:** `total = Σ score`, `max_total = 2 × len(criteria)`, `passed = total ≥ ceil(0.6 × max_total)`. The threshold lives in code so it's tunable without re-prompting.

### 8.4 What the review honestly is

One structured-output call scoring **structure, relevance to the spec, and code as read.** No execution, no tests run. The UI says so in one line under the score: *"Reviewed by reading the repo — nothing was run."* Judges respect this more than an implied CI pipeline.

### 8.5 GitHub fetch constraints

- Public `github.com/{owner}/{repo}` URLs only; optional `/tree/{branch}` ignored, default branch used.
- One request for repo metadata, one for the recursive tree, then raw fetches for README + up to **10 source files, ≤ 20 KB each, ≤ 60 KB total**, truncated with a marker. Skip binaries, lockfiles, `node_modules/`, `vendor/`, `dist/`, `.git/`, images.
- Friendly errors: private/404 → "That repo isn't public or doesn't exist" · empty → "That repo has no files yet" · rate-limited → "GitHub is rate-limiting us, try in a minute" · not a GitHub URL → inline validation.

### 8.6 Job-posting seed set — decision

**In, conditionally.** 15–20 real current postings, hand-copied as *excerpted requirement lists* (not full text) into `backend/seed/postings/*.txt`, each tagged with role ids. The analysis prompt receives 3–5 relevant excerpts as grounding.

**Condition:** it must be in the prompt from the **start** of Day 2 tuning. Adding context after dedup is tuned can re-break dedup. If the excerpts aren't ready by Day 2 morning, the seed set is out and the v3 judge answer stands unchanged.

Pitch line if in: *"Role requirements are grounded in a curated set of real current postings — the pipeline doesn't care where postings come from; live feeds are v2."* Explicitly not scraping, not an API, not live.

---

## 9. Fit % formula (changed in v4)

Computed in code on every read. Never from the model. Mirrored in TypeScript; both tested against one parity fixture that **must be rewritten for v4**.

```
WEIGHT = { core: 3, supporting: 1 }
DEPTH  = { full: 1.0, partial: 0.5 }

for each skill the role requires:
    w = WEIGHT[weight]
    total  += w
    earned += w * max(
        1.0 if verified else 0,            # passing repo submission
        0.5 if checked  else 0,            # self-report — was 1.0 in v3
        DEPTH[coverage_depth] or 0         # coursework
    )
fit = half_up(earned / total * 100)        # 0 when total == 0
```

**Why `max`, not `if/elif`:** the change request's priority chain would let a tick *lower* a fully-covered skill from 1.0 to 0.5. `max` keeps every signal monotonic — nothing the student does can reduce their score.

Consequences worth knowing:
- A tick on an uncovered skill: 0 → 0.5. A tick on a partial skill: no change (0.5 → 0.5). The demo ticks uncovered skills.
- Proof on a fully-covered skill: no change (already 1.0). Projects should target missing/ticked skills, which is why the project prompt is told the state of each skill.
- Ranking: fit desc, then model `rank` asc. Below 15% still displays as "Not enough foundation yet."

**Rejected alternative:** keep tick = 1.0 and add verified as a 1.5× bonus. Dirtier (fit could exceed 100 or needs renormalising) and doesn't fix the tick-everything problem. Logged in DECISIONS.md.

**Judge question:** *"Can't I just tick everything?"* → "You'll get to 50% on those skills. The other half is a repo that passes review. That's the whole point of the formula."

---

## 10. Screens

Three. No new screens; Prove It lives inside the drawer.

### 10.1 Setup — `/setup` · 10.2 Analyzing — `/analyzing`

Unchanged from v3.

### 10.3 Roadmap — `/roadmap` *(the money screen)*

Two-column desktop layout, unchanged: **left the ranking, right the role drawer.**

**Left column** — Section A "Your closest paths" (core), Section B "Worth considering" (adjacent) with bridge lines, **"what moved" strip** after any tick or passing submission. Cards gain a small **verified count** ("2 verified") when > 0.

**Right drawer — role detail**
- Header: title, one-liner, fit ring, bridge if adjacent
- **Missing skills** first, core before supporting: checkbox *"I've learned this"* · name · weight badge · real-world sentence. Skills that are verified show a **✓ Verified** badge instead of a checkbox (locked; nothing to tick).
- **Prove It** *(new, directly under Missing skills)*
  - First open: *"Designing your project…"* skeleton for 5–10 s (lazy generation). Every later open is instant.
  - Then: project title · spec paragraph · criteria list · *"Verifies:"* skill badges (these badges are the same skill rows as above, so the student sees exactly what moves).
  - Repo URL input (validates `github.com/owner/repo` inline) + **Submit for review** button. *"Reviewing…"* state for 15–60 s with the same staged-copy trick as the Analyzing screen.
  - After review: total / max, pass or not-yet badge, per-criterion score + one-line note, feedback paragraph, and the honesty line (*"Reviewed by reading the repo — nothing was run."*). On pass: verifies badges flip to ✓, the ring animates, **the left column re-sorts through the exact same animation path as a tick**, and the "what moved" strip fires. Resubmission allowed; latest review shown, all passes count.
- **Already covered by your courses**, collapsed by default.

**Live-update requirement (unchanged):** any change to ticks or verified skills recomputes every card and re-sorts Section A with a visible slide. Ticks update state optimistically; verified skills update only from the server's `/submit` response.

---

## 11. API surface

Seven endpoints. All except `/api/courses` require `X-Student-Id`.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/courses` | Catalog (public) |
| `POST` | `/api/students` | Create student → `{ student_id }` |
| `POST` | `/api/analyze` | The analysis call → `{ ok }` |
| `GET` | `/api/roadmap` | Everything: skills (with `checked`, `verified`), roles (with `fit_percent`, cached `project` or `null`, latest `review` or `null`), courses |
| `POST` | `/api/progress` | `{ skill_id, checked }` → `{ ok }` |
| `GET` | `/api/project?role_id=` *(new)* | Return cached project or generate + cache it |
| `POST` | `/api/submit` *(new)* | `{ role_id, repo_url }` → fetch + review → `{ review, verified_skill_ids }` |

`/api/roadmap` is fetched once. `/api/project` fills a hole in local state. `/api/submit` returns the full verified set so the client replaces, never merges.

---

## 12. Demo safety

### 12.1 Cached payloads — gated to the demo student

`DEMO_MODE=true` + `student.name == DEMO_STUDENT_NAME` caches three things, all in `contracts/fixtures/`:

| Fixture | Served by | Latency added |
|---|---|---|
| `demo_analysis.json` | `/analyze` | 6 s |
| `demo_project.json` | `/project` for the demo student's top role | 3 s |
| `demo_review.json` | `/submit` when `repo_url == DEMO_REPO_URL` | 4 s |

Any other student, role, or URL gets a real call — judges can try their own repo afterwards.

### 12.2 Canonical demo student

Ayesha · Semester 4 · CS201, CS301 (past) · CS401, CS402 (current) · AI, Databases, UI/UX Design. Unchanged.

**New, days before the slot:** generate her top role's project once (live), commit it as `demo_project.json`, then **build a real public repo that satisfies its criteria** (`DEMO_REPO_URL`). Run a live review against it; commit the passing result as `demo_review.json`. The project spec, the repo, and the cached review must agree — regenerate all three together if any changes.

### 12.3 Demo script (75 seconds)

**Check the hackathon's pitch time limit first.** If it's a hard 60 s, cut step 2 and shorten step 4's line.

1. **0:00** — Setup screen, pre-filled. *"A 4th-semester student. Two courses done, two in progress."*
2. **0:08** — *(3 s)* Point at the paste link: *"Different syllabus? Paste your own."*
3. **0:11** — Analyze. Analyzing screen (6 s).
4. **0:18** — Roadmap. *"Eight roles, ranked by how far along she already is. Not a quiz — computed from what her courses teach."*
5. **0:27** — Adjacent section, read one bridge line. *"She never asked for this one — the system found it."*
6. **0:36** — Click the top role. Drawer opens; Prove It is already there (cached). *"Covered. Missing. And a project designed for exactly her gaps."*
7. **0:44** — Tick three boxes. Cards shift a little. *"A tick moves it a little…"*
8. **0:50** — Paste the prepared repo URL, Submit. Reviewing state (4 s). *"…a repo that passes review moves it a lot."*
9. **0:57** — Review lands: skills flip to ✓, a role jumps visibly more than any tick did, "what moved" fires. *"Reviewed by reading the code — and every role that shares those skills just moved too."*
10. **1:12** — Stop talking.

Assign who clicks, who talks. Rehearse until it's comfortably under the limit.

---

## 13. Plan (3 core days + Day 4 for Prove It)

**Salman — backend, DB, deploy, GitHub fetch, `/submit`** · **Umer — three model calls, demo fixtures** · **Wahab — the entire frontend: Setup, Analyzing, Roadmap, drawer, animation, Prove It panel**

Prove It is **gated**: it starts only when Day 2's exit criteria are met (validated analysis fixture, dedup looks clean, the tick re-sort animation works against the fixture). If those slip, Prove It slips, not the core. **If you only have 3 days, Prove It is out** — the formula change alone is pointless without the verified path.

### Day 1 — Foundations *(unchanged from v3)*

Salman: DB, seed, identity, `/courses`, `/students`. Umer: analysis package with structured outputs → validated fixture + measured latency. Wahab: app shell, context, `scoring.ts`, `FitRing`, `RoleCard` on the fixture. All: contract agreed, hello-worlds deployed, CORS verified. **Seed postings (§8.6): whoever has slack copies excerpts tonight, or it's out.**

### Day 2 — Engine and the moment *(unchanged, plus the new parity fixture)*

All (morning): write **v4** `parity_cases.json` — must include verified > checked > coverage cases and the "tick on fully-covered skill does nothing" case. Salman: persistence, v4 `fit_percent`, `/roadmap`, `/progress`. Umer: retry logic, prompt tuning (dedup first), `demo_analysis.json`, `DEMO_MODE`. Wahab: two-column Roadmap, drawer, ticks, translateY re-sort, WhatMoved, Setup screen.

**Exit criteria (gate for Prove It):** tick in the drawer visibly re-sorts the left column · Python and TS fit agree on the v4 fixture · Setup posts a real student · analysis fixture has no near-duplicate skills on inspection.

### Day 3 — Integrate core, start Prove It

| Who | Work |
|---|---|
| Salman + Wahab (morning) | Wire Setup → Analyzing → Roadmap on the real API. Remove fixture mode. Deploy. **Core demo runs end-to-end on deployed URLs by lunch.** |
| Salman (afternoon) | `project` + `submission` tables, `GET /project`, `POST /submit` skeleton, `app/github.py` fetch with token, size caps, friendly errors |
| Umer (all day) | `ProjectOut` + `ReviewOut` schemas and validators, `project.py` and `review.py` calls with structured outputs, `passed` in code, prompt-injection framing, `run_project_cli.py` / `run_review_cli.py` for iteration. |
| Wahab (afternoon) | Analyzing screen. Prove It panel against a hand-written `demo_project.json` + `demo_review.json`: skeleton state, spec, criteria, verifies badges, URL input, reviewing state, result view, ✓ badges. `verifiedIds` in context. |

**Exit criteria:** core frozen and deployed. Prove It works locally against fixtures.

### Day 4 — Finish Prove It, freeze, rehearse

| Time | Work |
|---|---|
| Morning | Wire `/project` and `/submit` live. Umer generates the demo project live and commits it. **Salman builds the demo repo** (small, real, satisfies criteria). Umer runs a live review, commits `demo_review.json`. `DEMO_REPO_URL` set on the host. |
| Midday | Deploy. Run the full 75 s script on deployed URLs, twice. **HARD FREEZE.** |
| Afternoon | Visual pass. Rehearse ×3. README v2 section. DEMO.md updated. |
| Last 2 h | Buffer. |

**Cut order if Day 4 is at risk** (from the change request, kept as written):
1. Per-criterion notes → single feedback paragraph only.
2. Lazy project call → generate at analysis time for the top role only.
3. Whole feature → v2 README (formula reverts to v3; restore the v3 parity fixture from git).
**Never cut the formula parity tests.**

---

## 14. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Model emits duplicate/near-duplicate skills | **High** | Prompt dedup instruction; Day-2 tuning targets it first; seed postings only if in from the start |
| Analysis latency longer than expected | **High** | Measure Day 1; 240 s timeout; `DEMO_MODE`; Appendix B async fallback |
| Scope creep | **High** | §2 non-goals; Day 3 core freeze; Prove It gated |
| **Prove It eats Day 3 and the core isn't deployed** | **High** | Core deploys by Day 3 lunch before any Prove It work; cut order |
| **Demo repo doesn't pass the cached review on the day** | Medium | Review is cached for `DEMO_REPO_URL`; project, repo, and review committed together and never changed after |
| **GitHub rate limit during judge trials** | Medium | `GITHUB_TOKEN` (5000/h); ≤ 13 requests per submission |
| **Review call slow (≤ 60 KB input)** | Medium | Size cap; staged "Reviewing…" copy; 120 s client timeout |
| **Prompt injection via README** | Low | Delimited, "untrusted data" framing; it's a demo, not a grading system |
| Re-sort animation janky | Medium | Built Day 2 by Wahab, against a fixture; Prove It reuses it, no new animation |
| Two-service deploy/CORS failure | Medium | Hello-worlds Day 1 |
| Output truncated at `max_tokens` | Medium | 16k → 24k retry on `stop_reason == "max_tokens"` |
| Pitch runs over the time limit | Medium | Confirm the limit before Day 4; 60 s fallback script in DEMO.md |

---

## 15. Anticipated judge questions

**"Why is this an app and not a chat prompt?"**
Because of the loop. A chat can tell you a gap. It can't assign a project against *your* current gaps, take a repo back, score it against the same criteria, store the result, and shift every role that shares those skills — persistently, next week too. That loop is the product.

**"Did you actually run my code?"**
No, and the UI says so. The review reads structure, relevance to the spec, and code as written, through the GitHub API. Execution and tests are v2; the hard part — the shared skill vocabulary the score lands in — is already here.

**"Can't I just tick everything?"**
You'll reach 50% on those skills. The other half needs a repo that passes review. Self-report and proof weigh differently by design.

**"What if my syllabus is different?"** → Paste it. Any course can be overridden; custom courses can be added.

**"Won't role requirements go stale?"** → Roles are generated per student at analysis time [+ if seed set: grounded in a curated set of real current postings; live feeds are v2].

**"How do you know the fit % is accurate?"** → It isn't a model output; it's arithmetic over a weighted skill set (core ×3, partial ×0.5, tick ×0.5, verified ×1). Deterministic, identical every load.

**"Why did one repo change four cards?"** → All roles share one skill vocabulary. The project verifies skill ids, not a role; every role needing those ids moves.

**"Where's login?"** → Cut deliberately; one line in the data model.

**"What was the hardest part?"** → Keeping one skill vocabulary consistent across three separate model calls. Projects and reviews are forced to reference existing skill ids and validators hard-fail if they don't.

---

## 16. v2 (README only — do not build)

- Accounts (Supabase Auth, ES256 — TDD Appendix A)
- Run the repo: sandboxed execution, test detection, CI signals in the review
- Multiple projects per role; regenerate a project after skills change
- Courses page; per-course gap views
- File upload (DOCX/PDF syllabus) into the same curriculum field
- Add courses over time; "Re-analyze my path" preserving ticks and verifications
- Live job-posting signals (the pipeline already accepts posting excerpts)
- Peer comparison across a cohort; curated resource links per missing skill
