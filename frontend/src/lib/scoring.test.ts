import { describe, it, expect } from "vitest";
import { fitPercent } from "./scoring";
import parityCases from "../../../contracts/fixtures/parity_cases.json";

interface ParitySkill {
  weight: "core" | "supporting";
  coverage_depth: "full" | "partial" | null;
  checked: boolean;
  verified: boolean;
}

describe("fitPercent parity cases", () => {
  for (const c of parityCases.cases) {
    it(c.name, () => {
      const skills = (c.skills as ParitySkill[]).map((s) => ({
        weight: s.weight,
        coverageDepth: s.coverage_depth,
        checked: s.checked,
        verified: s.verified,
      }));
      expect(fitPercent(skills)).toBe(c.expected);
    });
  }
});
