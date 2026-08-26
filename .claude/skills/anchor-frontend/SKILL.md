---
name: anchor-frontend
description: How to build the ANCHOR React frontend — the Setup, Analyzing, and Roadmap screens, the role drawer, the Prove It panel (project spec, repo URL submit, review result, verified badges), the live re-sort animation, the "what moved" strip, the AnalysisContext state model with checkedIds and verifiedIds, the fixture-backed dev mode, and the fitPercent mirror. Use this for any task under frontend/, for anything mentioning React, Vite, Tailwind, shadcn, the drawer, the re-sort or slide animation, fit rings, checkboxes, localStorage, or the roadmap page.
---

# ANCHOR frontend

Design reference: `docs/TDD.md` §7. Shapes: `docs/CONTRACT.md` §3 and `src/lib/types.ts`.
The Roadmap page is the demo; treat its interaction quality as the product.

## State model — one mutable thing

```ts
checkedIds: Set<string>                       // optimistic, from ticks
verifiedIds: Set<string>                      // server-authoritative; REPLACED by /submit's verified_skill_ids
projects: Map<roleId, Project>                // display only, filled lazily by /project
reviews: Map<roleId, Review>                  // display only
roleFit = useMemo(...)                        // derived from data + checkedIds + verifiedIds
ordered = useMemo(...)                        // derived: core roles sorted by (-fit, rank)
openRoleSlug: string | null                   // which role the drawer shows (UI state, not data)
```

If you find yourself storing a fit %, a sort order, or "covered count" in state, stop —
derive it. That's why one tick updates every card, ring, and the strip with no sync code.

## The drawer is not a route

`RoleDrawer` renders inside `RoadmapPage`, to the right of the ranking, with the ranking
still visible and interactive (`<Sheet modal={false}>` or a fixed-width panel). `?role=slug`
in the URL is a convenience for reload; it never navigates away. If the drawer were a page,
the re-sort would happen off-screen and the demo would show nothing.

## The re-sort animation

```tsx
const pos = new Map(ordered.map((r, i) => [r.id, i]));
<div className="relative" style={{ height: coreRoles.length * CARD_H }}>
  {coreRoles.map(role => (                 // iterate the UNSORTED array — order never changes
    <div key={role.id}                     // key never changes
         className="absolute inset-x-0 transition-transform duration-500 ease-out"
         style={{ transform: `translateY(${pos.get(role.id)! * CARD_H}px)` }}>
      <RoleCard … />
    </div>
  ))}
</div>
```

Three things make it slide instead of snap: stable keys, stable iteration order, `transform`
not layout. Break any one and it snaps. `CARD_H` is a fixed pixel height; cards must not
grow with content — truncate the one-liner.

Fit ring: SVG circle, `strokeDasharray`, `transition-[stroke-dashoffset] duration-500`.

## Ticking a box

1. `toggle(skillId)` updates `checkedIds` synchronously.
2. `fetch POST /api/progress` fire-and-forget. On failure: revert the id, toast.
3. Nothing awaits the network. No refetch. No spinner.

Label the checkbox **"I've learned this"**. It is a self-assessment, and judges will ask.

## "What moved"

Keep previous `roleFit` and `pos` in a `useRef`. On change, pick the core role with the
largest `|Δfit|`; if its position changed, show `"Title 48% → 71% · #4 → #2"`, else just the
percentages. Fade after 4 s. Skip if `Δfit === 0`.

## Prove It panel (`ProveIt.tsx`, inside `RoleDrawer`, Day 3 afternoon)

Four states from `projects.get(roleId)` / `reviews.get(roleId)` / an in-flight flag: **loading** (skeleton, "Designing your project…", fire `loadProject` in `useEffect`) → **ready** (title, spec, criteria, "Verifies:" badges using `SkillRow`, URL input + Submit) → **reviewing** (input disabled, staged copy every 8 s) → **reviewed** (`total / max_total`, Passed / Not yet, per-criterion score pill + note, feedback, the honesty line *"Reviewed by reading the repo — nothing was run."*, input re-enabled).

- Validate `^https://github\.com/[\w.-]+/[\w.-]+/?$` before enabling Submit.
- On success: `setVerifiedIds(new Set(res.verified_skill_ids))`. Replace, never merge, never optimistic.
- Verified skills render ✓ Verified instead of a checkbox, everywhere. `RoleCard` shows "N verified".
- 422/502 render inline under the input; stay in **ready**.
- Zero new animation code. The left column re-sorts because `roleFit` depends on `verifiedIds`.

## Fixture-backed development

`VITE_USE_FIXTURE=true` makes `src/lib/api.ts` return `contracts/fixtures/roadmap_response.json`
for `GET /roadmap`, `contracts/fixtures/courses.json` for `GET /courses`, and `{ok:true}` /
`{student_id:"fixture"}` for POSTs. Build the whole Roadmap this way on Day 1–2. On Day 3
delete the flag from `.env` and the branch from `api.ts`.

## Rules

- `localStorage` only in `src/lib/identity.ts`. `fetch` only in `src/lib/api.ts`.
- Tailwind core utilities + shadcn. No CSS files. No component libraries beyond shadcn.
- No Redux, no React Query, no router-level data loaders.
- Desktop only. Don't spend time on breakpoints below 1024px.
- `src/lib/scoring.ts`: `earned += w * Math.max(verified ? 1 : 0, checked ? 0.5 : 0, DEPTH[depth] ?? 0)`; round with `Math.floor(x + 0.5)`. Run `npm test`.

## Definition of done for the Roadmap

- Open a role, tick 3 boxes: the drawer ring animates and at least one left-column card
  visibly slides past another, in the same frame, without a network round trip.
- "What moved" line appears and fades.
- Reloading `/roadmap?role=data-engineer` reopens the drawer with ticks persisted.
- `npm test` green.
