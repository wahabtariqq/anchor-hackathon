import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAnalysis } from "@/features/roadmap/AnalysisContext";
import { SkillRow } from "@/features/roadmap/SkillRow";
import { ApiError } from "@/lib/api";
import type { ProjectWithHistory, RoadmapRole, RoadmapSkill } from "@/lib/types";
import { SubmissionHistory } from "./SubmissionHistory";

const REPO_URL_RE = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;

interface ProjectCardProps {
  item: ProjectWithHistory;
  role: RoadmapRole;
  skillsById: Map<string, RoadmapSkill>;
  onResubmitted: () => void;
}

// One card per generated project, across every role at once (PRD-V2 §4.6) — resubmit reuses
// the exact submitRepo() the drawer's ProveIt panel uses, then asks the page to refetch.
export function ProjectCard({ item, role, skillsById, onResubmitted }: ProjectCardProps) {
  const { submitRepo, checkedIds, verifiedIds } = useAnalysis();
  const [expanded, setExpanded] = useState(false);
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const urlValid = REPO_URL_RE.test(url);

  function weightOf(skillId: string) {
    return role.skills.find((rs) => rs.skill_id === skillId)?.weight ?? "supporting";
  }

  async function handleSubmit() {
    if (!urlValid || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitRepo(role.id, url);
      setUrl("");
      onResubmitted();
    } catch (err) {
      setError(err instanceof ApiError && err.detail ? err.detail : "Review didn't complete — try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{role.title}</p>
            <h2 className="text-base font-semibold">{item.project.title}</h2>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "Hide spec" : "Show spec"}
          </Button>
        </div>

        {expanded && <p className="text-base text-muted-foreground">{item.project.spec}</p>}

        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">Verifies:</span>
          {item.project.verifies.map((skillId) => {
            const skill = skillsById.get(skillId);
            if (!skill) return null;
            return (
              <SkillRow
                key={skillId}
                skill={{ ...skill, checked: checkedIds.has(skillId), verified: verifiedIds.has(skillId) }}
                weight={weightOf(skillId)}
                variant="badge"
              />
            );
          })}
        </div>

        <SubmissionHistory submissions={item.submissions} />

        <div className="space-y-1.5 pt-1">
          <div className="flex gap-2">
            <Input
              placeholder="https://github.com/owner/repo"
              value={url}
              disabled={submitting}
              onChange={(e) => setUrl(e.target.value)}
            />
            <Button onClick={handleSubmit} disabled={!urlValid || submitting}>
              {submitting ? "Reviewing…" : item.submissions.length > 0 ? "Resubmit" : "Submit for review"}
            </Button>
          </div>
          {error && <p className="text-xs text-anchor-critical">{error}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
