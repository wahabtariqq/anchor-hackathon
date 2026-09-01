import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import type { RoadmapRole, RoadmapSkill } from "@/lib/types";
import { useAnalysis } from "./AnalysisContext";
import { SkillRow } from "./SkillRow";

const REPO_URL_RE = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;

const REVIEW_STAGES = ["Fetching the repo…", "Reading the structure…", "Scoring against the criteria…"];
const REVIEW_STAGE_MS = 8_000;

interface ProveItProps {
  role: RoadmapRole;
  skillsById: Map<string, RoadmapSkill>;
}

export function ProveIt({ role, skillsById }: ProveItProps) {
  const { projects, reviews, loadProject, submitRepo } = useAnalysis();
  const project = projects.get(role.id);
  const review = reviews.get(role.id);

  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reviewStage, setReviewStage] = useState(0);

  useEffect(() => {
    setLoadError(null);
    if (projects.has(role.id)) return;
    loadProject(role.id).catch((err: unknown) => {
      setLoadError(err instanceof ApiError ? err.message : "Couldn't design a project right now");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role.id, reloadKey]);

  useEffect(() => {
    if (!submitting) {
      setReviewStage(0);
      return;
    }
    const timers = [1, 2].map((i) => window.setTimeout(() => setReviewStage(i), i * REVIEW_STAGE_MS));
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [submitting]);

  async function handleSubmit() {
    if (!REPO_URL_RE.test(url) || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await submitRepo(role.id, url);
    } catch (err) {
      setSubmitError(
        err instanceof ApiError && err.detail ? err.detail : "Review didn't complete — try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function weightOf(skillId: string) {
    return role.skills.find((rs) => rs.skill_id === skillId)?.weight ?? "supporting";
  }

  const urlValid = REPO_URL_RE.test(url);

  return (
    <section>
      <h3 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">Prove it</h3>

      {!project ? (
        loadError ? (
          <div className="mt-2 space-y-2">
            <p className="text-sm text-muted-foreground">{loadError}</p>
            <Button variant="outline" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
              Retry
            </Button>
          </div>
        ) : (
          <div className="mt-2 space-y-2">
            <p className="text-sm text-muted-foreground">Designing your project…</p>
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-8 w-40" />
          </div>
        )
      ) : (
        <div className="mt-2 space-y-3">
          <div>
            <p className="text-sm font-semibold">{project.title}</p>
            <p className="mt-1 text-sm text-muted-foreground">{project.spec}</p>
          </div>

          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {project.criteria.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>

          <div className="flex flex-wrap gap-1.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">Verifies:</span>
            {project.verifies.map((skillId) => {
              const skill = skillsById.get(skillId);
              return skill ? (
                <SkillRow key={skillId} skill={skill} weight={weightOf(skillId)} variant="badge" />
              ) : null;
            })}
          </div>

          {review && (
            <div className="space-y-2 rounded-md border p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">
                  {review.total} / {review.max_total}
                </span>
                <Badge
                  variant="outline"
                  className={
                    review.passed
                      ? "border-anchor-good/40 bg-anchor-good/10 text-anchor-good"
                      : "text-muted-foreground"
                  }
                >
                  {review.passed ? "Passed" : "Not yet"}
                </Badge>
              </div>
              <div className="space-y-2">
                {review.criteria_scores.map((c) => (
                  <div key={c.criterion} className="text-sm">
                    <div className="flex items-baseline gap-2">
                      <Badge variant="outline" className="shrink-0 text-xs font-normal">
                        {c.score}/2
                      </Badge>
                      <span className="font-medium">{c.criterion}</span>
                    </div>
                    <p className="pl-1 text-muted-foreground">{c.note}</p>
                  </div>
                ))}
              </div>
              <p className="text-sm text-muted-foreground">{review.feedback}</p>
              <p className="text-xs italic text-muted-foreground">
                Reviewed by reading the repo — nothing was run.
              </p>
            </div>
          )}

          <div className="space-y-1.5">
            <div className="flex gap-2">
              <Input
                placeholder="https://github.com/owner/repo"
                value={url}
                disabled={submitting}
                onChange={(e) => setUrl(e.target.value)}
              />
              <Button onClick={handleSubmit} disabled={!urlValid || submitting}>
                {submitting ? "Reviewing…" : review ? "Resubmit" : "Submit for review"}
              </Button>
            </div>
            {submitting && <p className="text-xs text-muted-foreground">{REVIEW_STAGES[reviewStage]}</p>}
            {submitError && <p className="text-xs text-anchor-critical">{submitError}</p>}
          </div>
        </div>
      )}
    </section>
  );
}
