import type { ScoredSkillInput } from "./types";

const WEIGHT: Record<string, number> = { core: 3, supporting: 1 };
const DEPTH: Record<string, number> = { full: 1.0, partial: 0.5 };
const TICK = 0.5; // self-report earns half
const PROOF = 1.0; // passing repo submission earns full

export function fitPercent(skills: ScoredSkillInput[]): number {
  let earned = 0;
  let total = 0;
  for (const s of skills) {
    const w = WEIGHT[s.weight];
    total += w;
    // max, not if/elif: no signal may ever lower a score (verified/tick/coverage are monotonic).
    earned +=
      w *
      Math.max(
        s.verified ? PROOF : 0,
        s.checked ? TICK : 0,
        s.coverageDepth ? DEPTH[s.coverageDepth] : 0,
      );
  }
  if (total === 0) return 0;
  return Math.floor((earned / total) * 100 + 0.5); // half-up, matches Python's int(x + 0.5)
}
