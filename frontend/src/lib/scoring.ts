import type { ScoredSkillInput } from "./types";

const WEIGHT: Record<string, number> = { core: 3, supporting: 1 };
const DEPTH: Record<string, number> = { full: 1.0, partial: 0.5 };

export function fitPercent(skills: ScoredSkillInput[]): number {
  let earned = 0;
  let total = 0;
  for (const s of skills) {
    const w = WEIGHT[s.weight];
    total += w;
    if (s.checked) {
      earned += w;
    } else if (s.coverageDepth) {
      earned += w * DEPTH[s.coverageDepth];
    }
  }
  if (total === 0) return 0;
  return Math.floor((earned / total) * 100 + 0.5); // half-up, matches Python's int(x + 0.5)
}
