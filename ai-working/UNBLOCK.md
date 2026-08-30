# UNBLOCK — what you have to do, and what you don't

**Written 2026-08-30.** Companion to `HANDOFF.md`. That one says where the work is; this one
says what is stopping it and who can actually clear each thing.

Salman is busy, so everything below is written as: **can Umer clear this alone?**

---

## The headline: almost nothing is really blocked

I over-escalated one item and it propagated. Correcting it plainly:

> **`SkillState` was never a blocker.** I said I needed the four field names from Salman. They
> are in his committed code, `backend/app/routers/project.py:29-37`:
>
> ```python
> @dataclass(frozen=True)
> class SkillState:
>     slug: str
>     name: str
>     weight: str
>     state: str   # "verified" | "ticked" | "covered:full" | "covered:partial" | "missing"
> ```
>
> He builds it as `SkillState(slug=…, name=…, weight=…, state=…)`. **S6 can start immediately.**

With that gone, **S6, S7 and the remaining code work need nothing from anybody.** What is left
is a small number of *decisions* only you can make, and one genuinely large gap — deployment —
that nobody has started.

---

## Do these, in this order

### 1. Decide the seed postings — 2 minutes, closes S4 entirely

`backend/seed/postings/` contains only its README. PRD 8.6 admits the set **only if it is in the
prompt from the start of Day-2 tuning**, because adding grounding context after dedup is tuned
can re-break dedup. That window has passed.

**Recommendation: declare them OUT.** The reason the seed set existed was to make role
requirements defensible. The measured output is already clean without it — zero near-duplicate
skills and 60-72% cross-role reuse across three live runs — and the v3 judge answer stands
unchanged. Adding 15-20 hand-copied postings now buys a pitch line and risks the one quality
metric that is currently perfect.

**If OUT:** say so and I log a DECISIONS entry; S4 closes with no code.
**If IN:** you must hand-copy 15-20 real posting requirement lists into
`backend/seed/postings/*.txt`, first line `roles: <role-ids>`. I cannot invent these — PRD 8.6
says *real current postings*, and fabricating them would make the judge answer a lie.

### 2. Read `ai-working/prompts/analysis.md` — 10 minutes, highest value per minute

The v3 prompt text is lost, so I wrote this from scratch. **It is now driving the committed
`demo_analysis.json`, which drives the whole demo.** Nobody but me has read it.

Read the ```text block only. Ask yourself: are the skill-granularity rules right for your
students? Are the `real_world` examples the tone you want a judge to see on screen? Is the
adjacent-role framing what you meant? Changes are cheap now and expensive after S8.

### 3. Decide who builds the demo repo — unblocks S8

PRD 13 assigns it to Salman. `gh` here is authenticated as **Umer-prog with `repo` scope**, so
you can do it without him.

**The order is fixed and cannot be shortcut:**
1. S6 lands → run `run_project_cli.py` → commit `demo_project.json`
2. **Then** build a real public repo that satisfies *those* criteria
3. **Then** S7 lands → run `run_review_cli.py` against it → commit `demo_review.json`

The project spec, the repo and the cached review must agree, and PRD 14 lists "demo repo does
not pass the cached review on the day" as a live risk. I can write the repo's contents once
step 1 exists; you decide whether to push it under your account or hand it to Salman.

**Say the word and I will do steps 1-3 and hand you a ready repo to push.**

### 4. Deployment — the real gap, and it is not small

**Nothing is deployed and there is no deploy config anywhere.** No `Procfile`, `railway.json`,
`render.yaml` or `vercel.json`, and `frontend/.env.example` still says `VITE_USE_FIXTURE=true`
with the comment *"Delete on Day 3."*

TDD 10 wants both hello-worlds deployed on **Day 1, hour 2**. PRD 13 wants the core demo running
end to end on **deployed URLs by Day 3 lunch**. Neither has happened. This is Salman's lane and
it is the single biggest schedule risk left in the project — bigger than anything in mine.

**What you need to decide:** does Salman still own this, or do you take it? If you take it,
three things must be true before the pitch, and each is a separate failure mode:
- the API is deployed and reachable
- **`contracts/fixtures/` ships with it** — it sits *outside* `backend/`, and DEMO_MODE reads
  `demo_analysis.json` from it. A deploy that ships only `backend/` fails during the pitch.
- the frontend has `VITE_USE_FIXTURE` removed and `VITE_API_URL` pointed at the real API

### 5. The Appendix B question — cannot be answered until step 4

Worst measured analysis run was **101.8 s** against TDD 5.1's ~100 s host-proxy warning. But
**this is untestable while nothing is deployed** — the number that matters is your host's proxy
timeout, not mine.

Once deployed, the test is one command: hit `/api/analyze` on the deployed URL with
`DEMO_MODE=false` and see whether it completes or the proxy cuts it.

**If it cuts:** TDD Appendix B is ~40 backend lines and ~15 frontend lines, and it touches
`routers/analyze.py` — Salman's file. **If your pitch runs entirely in DEMO_MODE (6 s), this
never fires** and you can defer it. That is a legitimate choice; just make it deliberately
rather than by accident.

---

## What I can do right now without you

Say go on any of these:

| | Work | Needs |
|---|---|---|
| **S6** | `project.py`, validators, `generate_project`, `run_project_cli.py` | nothing — `SkillState` is known |
| **S7** | `review.py`, injection framing, `run_review_cli.py`, injection test | nothing |
| — | The 3 missing `parity_cases.json` cases TDD 8 names (*mixed depths*, *core-only*, *supporting-only*) | nothing; additive, ping Salman after |
| — | The `contract:` PR: PRD 4.3, TDD 4.7, TDD 9 and `.env.example` still describe the Anthropic SDK | nothing |
| — | Draft the demo repo's contents once `demo_project.json` exists | S6 first |

## What genuinely needs Salman

Only two things, and both are deployment:

1. **Deploying the API and frontend**, if he keeps that lane.
2. **The Appendix B implementation**, *if* step 5 shows the host cuts long requests — it edits
   `routers/analyze.py`, his file.

Everything else on the old blocker list is either resolved or yours to decide.

---

## Copy-paste for Salman when he surfaces

> Three things, none urgent for you today:
>
> 1. **Deploy status?** Nothing is deployed and there is no deploy config in the repo. TDD 10
>    wanted hello-worlds on Day 1 and PRD 13 wants the core on deployed URLs by Day 3 lunch.
>    Tell me if you want me to take it.
> 2. **When you deploy, `contracts/fixtures/` must ship too** — it is outside `backend/`, and
>    DEMO_MODE reads `demo_analysis.json` from it. Shipping only `backend/` breaks the demo path
>    during the pitch.
> 3. **Live analysis measured 53-102 s.** TDD 5.1 warns some hosts cut at ~100 s. Once deployed,
>    hit `/api/analyze` live once and see. If it cuts, that is Appendix B in your `analyze.py`.
>    If the pitch runs in DEMO_MODE it is 6 s and this never fires.
>
> FYI, nothing of yours changed: `app/config.py` gained three provider settings that default so
> the API still boots without them, and `tests/` gained four additive files. `/api/analyze` is
> live now — `demo_analysis.json` is a real 48-skill fixture, not the placeholder.
