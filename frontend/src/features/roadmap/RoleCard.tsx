import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FitRing } from "./FitRing";
import { cn } from "@/lib/utils";
import type { RoadmapRole, RoadmapSkill } from "@/lib/types";

interface RoleCardProps {
  role: RoadmapRole;
  fit: number;
  skillsById: Map<string, RoadmapSkill>;
  onClick?: () => void;
  className?: string;
}

function isCovered(skill: RoadmapSkill | undefined, checked: boolean): boolean {
  return checked || skill?.coverage_depth != null;
}

export function RoleCard({ role, fit, skillsById, onClick, className }: RoleCardProps) {
  const total = role.skills.length;
  const covered = role.skills.filter((rs) => {
    const skill = skillsById.get(rs.skill_id);
    return isCovered(skill, skill?.checked ?? false);
  }).length;

  const missingCore = role.skills
    .filter((rs) => rs.weight === "core" && !isCovered(skillsById.get(rs.skill_id), skillsById.get(rs.skill_id)?.checked ?? false))
    .slice(0, 2)
    .map((rs) => skillsById.get(rs.skill_id)?.name)
    .filter((n): n is string => Boolean(n));

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick?.();
      }}
      className={cn(
        "cursor-pointer transition-colors hover:border-foreground/20",
        role.proximity === "adjacent" && "border-dashed border-anchor-adjacent bg-anchor-adjacent/[0.06]",
        className,
      )}
    >
      <CardContent className="flex items-start gap-4 p-4">
        <FitRing percent={fit} size={48} strokeWidth={4} labelClassName="text-sm font-semibold" />
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold">{role.title}</h3>
          <p className="truncate text-sm text-muted-foreground">{role.one_liner}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {covered} of {total} skills covered
          </p>
          {missingCore.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
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
            <p className="mt-2 text-sm italic text-muted-foreground">{role.bridge}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
