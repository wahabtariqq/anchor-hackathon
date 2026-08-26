# frontend/ — React + Vite

**Wahab's lane — all of it.** Setup, Analyzing, and Roadmap are no longer split across three
people; one owner covers the entire frontend. Read `../docs/TDD.md` §7 before changing anything
here. Types in `src/lib/types.ts` mirror `../docs/CONTRACT.md` — if you change one, change the
other in the same PR.

## Layout

- `src/app/` — `App.tsx` (providers), `router.tsx` (three routes), `Resume.tsx` (localStorage → redirect logic).
- `src/lib/api.ts` — the only `fetch`. Injects `X-Student-Id`, 240s timeout. If `VITE_USE_FIXTURE=true`, serves `contracts/fixtures/*.json` instead.
- `src/lib/identity.ts` — the only `localStorage` access in the app.
- `src/lib/scoring.ts` — `fitPercent`. Mirror of `backend/app/scoring.py`. Tested against `contracts/fixtures/parity_cases.json`.
- `src/lib/types.ts` — **shared file**; mirrors `schemas.py`.
- `src/features/setup/` — `SetupPage`, `CourseCard`, `InterestChips`.
- `src/features/analyzing/` — Staged copy on a timer, decoupled from the request.
- `src/features/roadmap/` — `RoadmapPage` (two columns), `RoleCard`, `RoleDrawer`, `FitRing`, `SkillRow`, `WhatMoved`, `ProveIt`, `AnalysisContext`.
- `src/components/ui/` — shadcn output. Generated; don't hand-edit.

## Rules

- `checkedIds` (optimistic) and `verifiedIds` (server-authoritative, replaced wholesale by `/submit`) are the only state that affects numbers. Everything else is `useMemo` over them.
- `ProveIt.tsx` lives inside `RoleDrawer` with four states: loading / ready / reviewing / reviewed. It reuses `SkillRow` for verifies badges and never touches the animation code.
- The role drawer is **not a route**. It opens on the Roadmap page so the ranking stays visible while boxes are ticked.
- Re-sort uses absolute positioning + `translateY` with stable keys. Never reorder the array of DOM nodes.
- Ticking a box never awaits the network. `POST /api/progress` is fire-and-forget; revert + toast on failure.
- One `fetch` after load. No refetch on tick, no polling, no React Query.
- Tailwind core utilities and shadcn components only. No CSS files, no styled-components.

## Run / test

```bash
npm run dev                      # http://localhost:5173
npm test                         # vitest
npx shadcn@latest add sheet      # etc.
```
