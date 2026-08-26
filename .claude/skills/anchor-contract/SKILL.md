---
name: anchor-contract
description: The shared data contract for ANCHOR — analysis / project / review output schemas, API request/response shapes, the v4 fit % formula (max of verified, tick, coverage), fixtures, and the rules for changing any of them. Use this whenever a task touches schemas.py, types.ts, models.py, analysis/schema.py, anything in contracts/, any API response shape, the fit formula, or when two lanes (backend / AI / frontend) disagree about a field name, type, or enum. Also use it before writing any fixture JSON by hand.
---

# ANCHOR contract

The contract is `docs/CONTRACT.md`. Read it fully before continuing — it is short. This skill
tells you how to work with it, not what is in it.

## When you are asked to change a shape

1. Change `docs/CONTRACT.md` first.
2. Update every mirror in the same change:
   - `backend/app/schemas.py` (API models)
   - `backend/app/analysis/schema.py` (only if the model output changed)
   - `frontend/src/lib/types.ts`
   - any fixture in `contracts/fixtures/` that contains the changed field
3. Run `pytest -q` in `backend/` and `npm test` in `frontend/`.
4. Title the PR `contract: <what changed>` and tell the user to ping the group chat.

Never change one mirror alone "for now". A mismatch between `schemas.py` and `types.ts` is
invisible until the demo, which is the worst possible moment.

## When you are asked to write a fixture by hand

Copy the shape from `docs/CONTRACT.md` §3 exactly. Common mistakes:

- Roadmap `skills[].coverage_depth` is already collapsed to the best depth and may be `null`.
  The model output `coverage[].depth` is never null.
- Roadmap ids are DB ids (`sk_…`, `ro_…`, `sc_…`), not model slugs. Roles reference skills by
  the DB id.
- `bridge` is `""` for core roles, never `null`, never missing.
- Roles arrive **pre-sorted** by `(-fit_percent, rank)`. A hand-written fixture that is
  unsorted will make the UI look broken on first render.
- Make the demo fixture interesting: the demo requires ticking 3 skills to visibly move a
  role from ~#4 to ~#2. Put the same missing core skill in three or four roles so one tick
  moves several cards.

## When two lanes disagree

The contract wins. If the contract is silent, decide, write it into `docs/CONTRACT.md`, and
add a line to `docs/DECISIONS.md`. Do not resolve it in Slack alone.

## Fit formula gotchas

`max`, not `if/elif`. The v4 change request had an elif chain that let a tick lower a fully-covered skill; the contract uses `max` so no action lowers a score. The parity fixture must include `coverage_depth: "full", checked: true → 1.0` and `verified` cases.

### Rounding

Python `round()` is banker's rounding; JS `Math.round()` is half-up. Both implementations
use explicit half-up (`int(x + 0.5)` / `Math.floor(x + 0.5)`). If you see parity tests
disagreeing by exactly 1, this is why.

## Quick reference

| Question | Answer |
|---|---|
| Where do enums live? | `docs/CONTRACT.md` §5 |
| Which file is the model output schema? | `backend/app/analysis/schema.py` (`AnalysisOut`) |
| Which file is the roadmap response? | `backend/app/schemas.py` (`RoadmapResponse`) ↔ `frontend/src/lib/types.ts` |
| How does the frontend run without the backend? | `VITE_USE_FIXTURE=true` reads `contracts/fixtures/roadmap_response.json` |
| Who regenerates `roadmap_response.json`? | Dev A, `python scripts/dump_roadmap.py --student <id>` |
