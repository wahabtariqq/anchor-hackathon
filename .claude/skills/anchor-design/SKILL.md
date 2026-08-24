---
name: anchor-design
description: >
  ANCHOR-specific visual language — color tokens, typography/spacing scale,
  and the exact mandated constants for re-sort, fit ring, and badge styling.
  Use before choosing colors, spacing, or animation timing anywhere in
  frontend/src. Defers motion methodology to apple-design and chart/meter/
  color methodology to dataviz — this file has ANCHOR's decisions, not the
  general technique.
---

# ANCHOR design

Read this file first for ANCHOR's specifics. For *method* this file doesn't
re-derive, go to the source skill instead of guessing:

- **`apple-design`** — motion/gesture physics: spring feel, sheet/drawer
  interaction, interruptible transitions, optical type sizing, reduced-motion
  patterns. Consult it when refining the drawer open/close feel or checkbox
  tick micro-feedback (Day 7).
- **`dataviz`** — chart/meter/color methodology. The palette below is derived
  from `dataviz`'s validated default palette (`references/palette.md`) —
  those hexes already pass the CVD/contrast validator, so don't re-pick
  colors by eye. If a new meter or stat-tile gets added later, use
  `dataviz`'s procedure, not intuition.

This file only records ANCHOR-specific decisions: things PRD/TDD already
mandate verbatim, and the handful of choices (palette, type scale, spacing)
the docs deliberately left open. A grep of PRD/TDD/CONTRACT/DEMO found zero
color, hex, or font specification anywhere — everything under "New decision"
below is this skill's own call, not a mirror of a doc.

---

## 1. Mandated constants (non-negotiable — already decided in PRD/TDD)

| What | Spec |
|---|---|
| Re-sort container | Absolute positioning inside a `relative` div sized `coreRoles.length * CARD_H`. Iterate roles in **stable, unchanging order**; each card `transition-transform duration-500 ease-out`, `transform: translateY(pos * CARD_H)`. Reordering the array instead of the position map makes it *snap*, not slide — verify visually, no test catches this. |
| `CARD_H` | Fixed pixel constant (set in `RoadmapPage.tsx`, see §3). Card content must never grow — truncate the one-liner to one line. |
| `FitRing` | SVG `<circle>`, `strokeDasharray`/`strokeDashoffset`, `transition-[stroke-dashoffset] duration-500`. |
| Adjacent-role cards | Dashed border + lighter background (§2 gives the exact token). |
| Missing **core**-skill badges | Red-tinted (§2 gives the exact token). Missing *supporting* skills are not color-mandated — keep them neutral (see §2). |
| Checkbox copy | Exactly **"I've learned this"** — this is also the accessible name, not just visible text. |
| Component policy | shadcn components + Tailwind **core** utilities only. No custom CSS files beyond `index.css`, no other UI/animation library. |
| Layout | Desktop only. Design target 1024px+, no responsive breakpoints below it. |

---

## 2. Color palette / semantic tokens — New decision

Source: `dataviz`'s **status palette** (good/warning/serious/critical — fixed,
mode-invariant, pre-validated) for meaning-carrying colors, plus **categorical
slot 1 (blue)** for the one non-status accent (adjacent-role discovery cue)
and the **sequential blue ramp** for the fit ring. Nothing here needed
re-validation — these are the reference skill's already-passing hexes, used
unmodified.

Add these as CSS custom properties in `frontend/src/index.css`, **alongside**
the existing shadcn slate theme vars (`--background`, `--foreground`,
`--border`, etc.) — those still govern all neutral chrome (buttons, inputs,
default card). Add, don't replace.

```css
:root {
  /* status-derived semantic tokens (dataviz reference palette, mode-invariant hex) */
  --anchor-good: 120 86% 34%;        /* #0ca30c — covered/full, checked */
  --anchor-critical: 0 61% 52%;      /* #d03b3b — missing core-skill badge */

  /* adjacent-role discovery accent (dataviz categorical slot 1) */
  --anchor-adjacent: 213 68% 50%;    /* #2a78d6 light */

  /* fit-ring sequential ramp (dataviz sequential blue) */
  --anchor-ring-fill: 213 68% 50%;   /* #2a78d6 — step 450 */
  --anchor-ring-track: 213 78% 84%;  /* #b7d3f6 — step 150, lighter step of same ramp */
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --anchor-adjacent: 213 77% 56%;   /* #3987e5 dark */
    --anchor-ring-fill: 213 77% 56%;  /* #3987e5 dark */
    --anchor-ring-track: 213 40% 25%; /* muted dark step, same hue family — approximated, not a literal dataviz step */
  }
}
:root[data-theme="dark"] {
  --anchor-adjacent: 213 77% 56%;
  --anchor-ring-fill: 213 77% 56%;
  --anchor-ring-track: 213 40% 25%;
}
```

**Usage map:**

| Element | Token | Notes |
|---|---|---|
| Missing core-skill badge | `--anchor-critical` (text+border), ~10% tint background | Only *core*-weight missing skills. Supporting-weight missing skills use the neutral `muted` shadcn token — don't extend red to them, it dilutes the "core" signal. |
| Covered/full skill marker | `--anchor-good` | Solid checkmark icon + token color. |
| Covered/partial skill marker | **muted ink, not a color** (shadcn `muted-foreground`) + an outline/half-filled icon | Deliberately no dedicated hue — a third status color between red and green would blur two signals that already read cleanly. Per dataviz: identity/state should never ride on a color the reader has to learn; full vs. partial reads from the icon, not a new hue. |
| "I've learned this" checked state | `--anchor-good` on the checkbox check mark | The checkbox + label is the primary signal; color is a reinforcing accent, never load-bearing alone. |
| Adjacent-role card | dashed `--anchor-adjacent` border, `--anchor-adjacent` at ~6% tint background | Core-role cards get **no** accent — neutral shadcn `card` styling is the default state; the accent exists only to mark "adjacent" as different. |
| `FitRing` fill | `--anchor-ring-fill` | Single hue across all fit tiers (sequential magnitude encoding, not severity) — the "Not enough foundation yet" copy at <15% carries that meaning in text, not in a ring recolor. Keeps the ring from competing with the red/green status vocabulary. |
| `FitRing` track (unfilled) | `--anchor-ring-track` | Lighter step of the same ramp, per dataviz meter spec ("fill + track share one ramp"). |

Never use `--anchor-critical`/`--anchor-good` as body text color for
non-status text (dataviz rule: *text wears text tokens, never the data
color*) — they're for the badge/icon/ring itself, not surrounding copy.

---

## 3. Typography scale — New decision

No custom sizes — use Tailwind's default `text-*` scale only (matches the
shadcn-only / Tailwind-core-only rule). Assignments:

| Element | Class |
|---|---|
| Fit-% numeral (inside `FitRing`) | `text-2xl font-semibold` (drawer header), `text-lg font-semibold` (role card) |
| Role title | `text-base font-semibold` |
| One-liner (role card, truncated to 1 line) | `text-sm text-muted-foreground truncate` |
| Section headers ("Your closest paths" / "Worth considering") | `text-sm font-medium uppercase tracking-wide text-muted-foreground` |
| Badge text | `text-xs font-medium` |
| Real-world sentence (`SkillRow`) | `text-sm text-muted-foreground` |
| Bridge line (adjacent role, italic) | `text-sm italic` |

Consult `apple-design` if any of these feel visually off at build time
(optical sizing / tracking refinement) — Day 7 polish pass, not before.

## 4. Spacing scale — New decision

Tailwind default spacing scale only (4px increments). No arbitrary values
except `CARD_H` itself, which is a JS constant (not a Tailwind class) because
the re-sort math needs a literal number:

```ts
// frontend/src/features/roadmap/RoadmapPage.tsx
const CARD_H = 132; // px — role card height incl. gap; keep card content within this or it clips
```

| Element | Spacing |
|---|---|
| Card padding | `p-4` |
| Inter-card gap (baked into `CARD_H`, not a flex `gap-*`) | 12px of `CARD_H`'s 132px is reserved as the visual gap between stacked cards |
| Two-column gutter (`RoadmapPage`) | `gap-6` |
| Drawer padding | `p-6` |
| Section spacing (A vs. B, header vs. body) | `space-y-6` |

---

## 5. Motion inventory (index — method lives in `apple-design`)

| Element | Timing (mandated) | Notes |
|---|---|---|
| Re-sort `translateY` | `duration-500 ease-out` | Fixed by TDD §7.3. |
| `FitRing` stroke-dashoffset | `duration-500` | Fixed by TDD §7.3. |
| `WhatMoved` fade | appears on change, fades after 4s | Fixed by PRD §10.3. |
| Drawer open/close | not fixed | Consult `apple-design` Day 7 — sheet/drawer interruptible-transition pattern. |
| Checkbox tick micro-feedback | not fixed | Consult `apple-design` Day 7 — keep subtle, the re-sort is the feedback that matters. |
| Reduced motion | not fixed | Guard `translateY` and `stroke-dashoffset` transitions with `motion-reduce:transition-none` (Tailwind variant) — pattern per `apple-design`. |

---

## 6. Meter & stat-tile inventory (index — method lives in `dataviz`)

| Element | Spec |
|---|---|
| `FitRing` | See §2 for tokens. Per dataviz meter spec: fill = accent hue, track = lighter step of the same ramp — implemented here as `--anchor-ring-fill` / `--anchor-ring-track`. |
| "X of Y skills covered" | Plain text stat, no color — `text-sm text-muted-foreground` per §3. Not a stat-tile (no delta/trend needed). |
| Missing/covered skill badges | See §2's usage map — these are the "status" role in dataviz terms (good/critical), not categorical. |

---

## 7. Empty / loading / error state look — New decision

Standardize on shadcn `Skeleton` for loading, and one consistent empty-copy
voice (short, factual, matches PRD's plain-spoken tone — see PRD §12.3
demo script for the register to match):

| State | Look |
|---|---|
| Roadmap loading (pre-fetch) | `Skeleton` blocks matching the two-column card grid shape, not a spinner. |
| Roadmap 404 (no analysis yet) | Redirect to `/setup` per `Resume.tsx` — no visible empty state needed, this is a redirect not a render. |
| Setup validation errors | Inline, next to the offending field — shadcn form patterns, red `--anchor-critical` text only on the error message itself, not the whole field border (keep it calm). |
| Analyzing failure | Full-screen message + **"Try again"** button (PRD §10.2) — no red/critical color needed here, this is an expected retry path, not an alarm. |

---

## 8. Accessibility notes specific to ANCHOR

(Full detail in the frontend plan, Day 7 — indexed here for quick reference
while building.)

- Checkbox: confirm "I've learned this" is the **accessible name**, not just
  adjacent visible text (`<label htmlFor>` or `aria-labelledby`).
- Drawer: `Sheet modal={false}` deliberately disables Radix's focus trap so
  the ranking stays interactive — move focus to the drawer title on open,
  return it to the triggering `RoleCard` on close (must be done by hand).
- Re-sort has **no accessible signal by default** (transform-only, DOM order
  never changes) — add a visually-hidden `aria-live="polite"` region that
  mirrors `WhatMoved`'s text so a screen-reader user hears the rank change.
- Reduced motion: see §5.
- Contrast: `--anchor-critical` (#d03b3b) and `--anchor-good` (#0ca30c) are
  dataviz's pre-validated status hexes — already checked against light/dark
  chart surfaces. Re-check against the actual shadcn `background`/`card`
  tokens they render on here if the badge background tint changes.

---

## 9. Component checklist

| File | Sections that apply |
|---|---|
| `FitRing.tsx` | §1 (SVG spec), §2 (ring tokens), §5 (dashoffset timing) |
| `RoleCard.tsx` | §1 (CARD_H, re-sort), §2 (adjacent accent, missing-core badges), §3, §4 |
| `RoleDrawer.tsx` | §1 (not a route), §2 (bridge line, badges), §8 (focus management) |
| `SkillRow.tsx` | §2 (covered/missing/checked tokens), §3 (real-world sentence size) |
| `WhatMoved.tsx` | §5 (4s fade), §8 (aria-live mirror) |
| `CourseCard.tsx` | §3, §4, §7 (validation error look) |
| `InterestChips.tsx` | §3, §4 |
| `AnalyzingPage.tsx` | §7 (failure state, no alarm color) |
