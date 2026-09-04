import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FitRing } from "./FitRing";
import { cn } from "@/lib/utils";
import type { RoadmapRole, RoadmapSkill } from "@/lib/types";

interface RoleCardProps {
  role: RoadmapRole;
  fit: number;
  skillsById: Map<string, RoadmapSkill>;
  /** True when this role's detail is the one currently open in the drawer. */
  selected?: boolean;
  onClick?: () => void;
  className?: string;
}

function isCovered(skill: RoadmapSkill | undefined): boolean {
  return Boolean(skill && (skill.checked || skill.verified || skill.coverage_depth != null));
}

export function RoleCard({ role, fit, skillsById, selected = false, onClick, className }: RoleCardProps) {
  const total = role.skills.length;
  const covered = role.skills.filter((rs) => isCovered(skillsById.get(rs.skill_id))).length;
  const verifiedCount = role.skills.filter((rs) => skillsById.get(rs.skill_id)?.verified).length;

  const missingCore = role.skills
    .filter((rs) => rs.weight === "core" && !isCovered(skillsById.get(rs.skill_id)))
    .slice(0, 2)
    .map((rs) => skillsById.get(rs.skill_id)?.name)
    .filter((n): n is string => Boolean(n));

  return (
    <Card
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick?.();
      }}
      className={cn(
        "cursor-pointer transition-all duration-150 hover:border-foreground/20",
        role.proximity === "adjacent" && "border-dashed border-anchor-adjacent bg-anchor-adjacent/[0.06]",
        selected &&
          "border-primary/60 bg-primary/[0.05] shadow-md ring-1 ring-primary/30 hover:border-primary/60",
        className,
      )}
    >
      <CardContent className="flex items-start gap-5 p-5">
        <FitRing percent={fit} size={48} strokeWidth={4} labelClassName="text-sm font-semibold" />
        <div className="min-w-0 flex-1 space-y-1">
          <h3 className="truncate font-display text-base font-semibold">{role.title}</h3>
          <p className="truncate text-base text-muted-foreground">{role.one_liner}</p>
          <p className="text-xs text-muted-foreground">
            {covered} of {total} skills covered
            {verifiedCount > 0 && <span className="text-anchor-good"> · {verifiedCount} verified</span>}
          </p>
          {missingCore.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {missingCore.map((name) => (
                <Badge
                  key={name}
                  variant="outline"
                  className="border-anchor-critical/40 bg-anchor-critical/10 text-anchor-critical"
                >
                  {name}
                </Badge>
              ))}
            </div>
          )}
          {role.proximity === "adjacent" && role.bridge && (
            <p className="pt-1 text-sm italic text-muted-foreground">{role.bridge}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
