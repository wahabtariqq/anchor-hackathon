import { useEffect, useRef, useState } from "react";
import { ChevronDown, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { RoadmapRole, RoadmapSkill } from "@/lib/types";
import { FitRing } from "./FitRing";
import { ProveIt } from "./ProveIt";
import { SkillRow, skillState } from "./SkillRow";

interface RoleDrawerProps {
  role: RoadmapRole;
  fit: number;
  skillsById: Map<string, RoadmapSkill>;
  onToggleSkill: (skillId: string) => void;
  onClose: () => void;
  className?: string;
}

export function RoleDrawer({ role, fit, skillsById, onToggleSkill, onClose, className }: RoleDrawerProps) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [coveredOpen, setCoveredOpen] = useState(false);

  // Focus the drawer whenever a different role opens (anchor-design §8) — since
  // RoleDrawer stays mounted for the drawer's lifetime, a role change is a prop swap,
  // not a mount, so this can't rely on a mount-only effect.
  useEffect(() => {
    titleRef.current?.focus();
  }, [role.id]);

  const bySkillId = (id: string) => skillsById.get(id);

  const missing = role.skills
    .filter((rs) => {
      const skill = bySkillId(rs.skill_id);
      if (!skill) return false;
      const s = skillState(skill);
      return s === "verified" || s === "ticked" || s === "missing";
    })
    .sort((a, b) => (a.weight === b.weight ? 0 : a.weight === "core" ? -1 : 1));

  const covered = role.skills
    .filter((rs) => {
      const skill = bySkillId(rs.skill_id);
      if (!skill) return false;
      const s = skillState(skill);
      return s === "covered-full" || s === "covered-partial";
    })
    .sort((a, b) => (a.weight === b.weight ? 0 : a.weight === "core" ? -1 : 1));

  return (
    <div className={cn("flex h-full flex-col overflow-y-auto rounded-lg border bg-card p-6", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2
            ref={titleRef}
            tabIndex={-1}
            className="font-display text-lg font-semibold outline-none"
          >
            {role.title}
          </h2>
          <p className="mt-0.5 text-sm text-muted-foreground">{role.one_liner}</p>
          {role.proximity === "adjacent" && role.bridge && (
            <p className="mt-2 text-sm italic text-muted-foreground">{role.bridge}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <FitRing percent={fit} size={56} labelClassName="text-lg font-semibold" />
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close role details">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Separator className="my-4" />

      <section>
        <h3 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
          Missing skills
        </h3>
        <div className="mt-1 divide-y">
          {missing.length === 0 ? (
            <p className="py-2 text-sm text-muted-foreground">Nothing missing — every skill here is covered.</p>
          ) : (
            missing.map((rs) => (
              <SkillRow
                key={rs.skill_id}
                skill={bySkillId(rs.skill_id)!}
                weight={rs.weight}
                onToggle={onToggleSkill}
              />
            ))
          )}
        </div>
      </section>

      <Separator className="my-4" />

      <ProveIt role={role} skillsById={skillsById} />

      {covered.length > 0 && (
        <>
          <Separator className="my-4" />
          <Collapsible open={coveredOpen} onOpenChange={setCoveredOpen}>
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center justify-between text-sm font-medium uppercase tracking-wide text-muted-foreground"
              >
                Already covered by your courses ({covered.length})
                <ChevronDown className={cn("h-4 w-4 transition-transform", coveredOpen && "rotate-180")} />
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-1 divide-y">
              {covered.map((rs) => (
                <SkillRow key={rs.skill_id} skill={bySkillId(rs.skill_id)!} weight={rs.weight} />
              ))}
            </CollapsibleContent>
          </Collapsible>
        </>
      )}
    </div>
  );
}
