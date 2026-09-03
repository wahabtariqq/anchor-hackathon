import { Check, CircleDot } from "lucide-react";
import { skillState, type SkillState } from "@/features/roadmap/SkillRow";
import { cn } from "@/lib/utils";
import type { Depth } from "@/lib/types";

// Maps SkillRow.tsx's shared skillState() precedence (DECISIONS #34: verified > covered:full >
// ticked > covered:partial > missing) onto PRD-V2 §4.5's five status labels — reused, not
// re-derived, so this screen can never disagree with the Roadmap drawer about a skill's state.
const LABELS: Record<SkillState, string> = {
  verified: "Verified",
  "covered-full": "Covered",
  ticked: "Learned",
  "covered-partial": "Partial",
  missing: "Missing",
};

interface StatusPillProps {
  skill: { verified: boolean; coverage_depth: Depth | null; checked: boolean };
  className?: string;
}

export function StatusPill({ skill, className }: StatusPillProps) {
  const state = skillState(skill);

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        (state === "verified" || state === "covered-full" || state === "ticked") &&
          "border-anchor-good/40 bg-anchor-good/10 text-anchor-good",
        (state === "covered-partial" || state === "missing") && "text-muted-foreground",
        className,
      )}
    >
      {state === "verified" && <Check className="h-3 w-3" aria-hidden />}
      {state === "covered-full" && <CircleDot className="h-3 w-3" aria-hidden />}
      {LABELS[state]}
    </span>
  );
}
