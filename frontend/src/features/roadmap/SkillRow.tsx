import { Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { RoadmapSkill, Weight } from "@/lib/types";

// Precedence per DECISIONS #34: verified > covered:full > ticked > covered:partial > missing.
// A skill can only ever render one of these at a time.
export type SkillState = "verified" | "covered-full" | "ticked" | "covered-partial" | "missing";

export function skillState(skill: Pick<RoadmapSkill, "verified" | "coverage_depth" | "checked">): SkillState {
  if (skill.verified) return "verified";
  if (skill.coverage_depth === "full") return "covered-full";
  if (skill.checked) return "ticked";
  if (skill.coverage_depth === "partial") return "covered-partial";
  return "missing";
}

interface SkillRowProps {
  skill: RoadmapSkill;
  weight: Weight;
  onToggle?: (skillId: string) => void;
  /** "row" (default): full drawer row. "badge": compact pill for Prove It's "Verifies:" list. */
  variant?: "row" | "badge";
  className?: string;
}

export function SkillRow({ skill, weight, onToggle, variant = "row", className }: SkillRowProps) {
  const state = skillState(skill);

  if (variant === "badge") {
    const isDone = state === "verified" || state === "covered-full" || state === "ticked";
    return (
      <Badge
        variant="outline"
        className={cn(
          "gap-1 px-2.5 py-1 text-xs font-medium",
          isDone
            ? "border-anchor-good/40 bg-anchor-good/10 text-anchor-good"
            : "text-muted-foreground",
          className,
        )}
      >
        {isDone && <Check className="h-3 w-3" />}
        {skill.name}
      </Badge>
    );
  }

  const inputId = `skill-${skill.id}`;

  return (
    <div className={cn("flex items-start gap-3 py-2", className)}>
      <div className="flex h-5 w-5 shrink-0 items-center justify-center">
        {state === "verified" ? (
          <Check className="h-4 w-4 text-anchor-good" aria-hidden />
        ) : state === "covered-partial" ? (
          <span
            aria-hidden
            className="h-3 w-3 rounded-full border-2 border-muted-foreground/50"
            style={{
              background:
                "linear-gradient(90deg, hsl(var(--muted-foreground)) 50%, transparent 50%)",
            }}
          />
        ) : (
          <Checkbox
            id={inputId}
            checked={state === "ticked"}
            onCheckedChange={() => onToggle?.(skill.id)}
          />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          {state === "verified" ? (
            <span className="text-sm font-medium text-anchor-good">✓ Verified</span>
          ) : state === "covered-partial" ? (
            <span className="text-sm font-medium text-muted-foreground">Partially covered</span>
          ) : (
            <Label htmlFor={inputId} className="cursor-pointer text-sm font-medium">
              I've learned this
            </Label>
          )}
          <span className="text-sm font-semibold">{skill.name}</span>
          <span className="text-xs uppercase tracking-wide text-muted-foreground">{weight}</span>
        </div>
        <p className="text-sm text-muted-foreground">{skill.real_world}</p>
      </div>
    </div>
  );
}
