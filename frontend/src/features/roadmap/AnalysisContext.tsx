import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { getProject, getRoadmap, setProgress, submitRepo as apiSubmitRepo } from "@/lib/api";
import { recordSnapshotIfChanged, recordSubmission, recordTick } from "@/lib/eventLog";
import { setStudentName } from "@/lib/identity";
import { fitPercent } from "@/lib/scoring";
import type { ProjectResponse, ReviewResponse, RoadmapResponse } from "@/lib/types";

interface AnalysisContextValue {
  data: RoadmapResponse | null;
  loading: boolean;
  error: string | null;
  checkedIds: Set<string>;
  verifiedIds: Set<string>;
  toggle: (skillId: string) => void;
  projects: Map<string, ProjectResponse>;
  reviews: Map<string, ReviewResponse>;
  loadProject: (roleId: string) => Promise<void>;
  submitRepo: (roleId: string, url: string) => Promise<void>;
  roleFit: Map<string, number>;
  openRoleSlug: string | null;
  setOpenRole: (slug: string | null) => void;
}

const AnalysisContext = createContext<AnalysisContextValue | null>(null);

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<RoadmapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  // Server-authoritative: seeded on load, then only ever replaced wholesale by a
  // passing /submit response (never merged, never toggled locally like checkedIds).
  const [verifiedIds, setVerifiedIds] = useState<Set<string>>(new Set());
  // Display data only — never read by roleFit. Seeded from each role's own
  // project/latest_review (already generated in an earlier session), then filled in
  // lazily by loadProject/submitRepo.
  const [projects, setProjects] = useState<Map<string, ProjectResponse>>(new Map());
  const [reviews, setReviews] = useState<Map<string, ReviewResponse>>(new Map());
  const [openRoleSlug, setOpenRoleSlug] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getRoadmap()
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setStudentName(res.student.name);
        setCheckedIds(new Set(res.skills.filter((s) => s.checked).map((s) => s.id)));
        setVerifiedIds(new Set(res.skills.filter((s) => s.verified).map((s) => s.id)));
        setProjects(new Map(res.roles.filter((r) => r.project).map((r) => [r.id, r.project!])));
        setReviews(new Map(res.roles.filter((r) => r.latest_review).map((r) => [r.id, r.latest_review!])));
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load roadmap");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // checkedIds (optimistic) and verifiedIds (server-authoritative) are the only two
  // mutable sets that drive numbers (per anchor-frontend skill). roleFit is always
  // derived from them — never stored separately.
  const roleFit = useMemo(() => {
    const m = new Map<string, number>();
    if (!data) return m;
    const cov = new Map(data.skills.map((s) => [s.id, s.coverage_depth]));
    for (const role of data.roles) {
      m.set(
        role.id,
        fitPercent(
          role.skills.map((rs) => ({
            weight: rs.weight,
            coverageDepth: cov.get(rs.skill_id) ?? null,
            checked: checkedIds.has(rs.skill_id),
            verified: verifiedIds.has(rs.skill_id),
          })),
        ),
      );
    }
    return m;
  }, [data, checkedIds, verifiedIds]);

  // Simulated event/snapshot log (lib/eventLog.ts) — makes the V2 Dashboard react to real
  // ticks/submissions without a backend. This effect reuses WhatMoved.tsx's own technique (diff
  // against a ref of the previous roleFit map) to detect "what changed" and write one snapshot
  // per role whose fit actually moved; the very first render has no previous map, so nothing is
  // written on load, only on real change.
  const prevRoleFit = useRef<Map<string, number> | null>(null);
  useEffect(() => {
    if (prevRoleFit.current) {
      for (const [roleId, fit] of roleFit) {
        recordSnapshotIfChanged(roleId, prevRoleFit.current.get(roleId), fit);
      }
    }
    prevRoleFit.current = roleFit;
  }, [roleFit]);

  function toggle(skillId: string) {
    const wasChecked = checkedIds.has(skillId);

    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (wasChecked) next.delete(skillId);
      else next.add(skillId);
      return next;
    });
    recordTick(data?.skills.find((s) => s.id === skillId)?.name ?? skillId, !wasChecked);

    // Fire-and-forget: nothing awaits the network, the visual update is already committed above.
    setProgress({ skill_id: skillId, checked: !wasChecked }).catch(() => {
      setCheckedIds((cur) => {
        const reverted = new Set(cur);
        if (wasChecked) reverted.add(skillId);
        else reverted.delete(skillId);
        return reverted;
      });
      toast.error("Couldn't save that — try again.");
    });
  }

  async function loadProject(roleId: string): Promise<void> {
    if (projects.has(roleId)) return;
    const project = await getProject(roleId);
    setProjects((prev) => new Map(prev).set(roleId, project));
  }

  async function submitRepo(roleId: string, url: string): Promise<void> {
    const res = await apiSubmitRepo({ role_id: roleId, repo_url: url });
    setReviews((prev) => new Map(prev).set(roleId, res.review));
    // Replace wholesale, never merge — this is the server's full verified set.
    setVerifiedIds(new Set(res.verified_skill_ids));
    recordSubmission(
      data?.roles.find((r) => r.id === roleId)?.title ?? roleId,
      url,
      res.review.total,
      res.review.max_total,
      res.review.passed,
    );
  }

  const value: AnalysisContextValue = {
    data,
    loading,
    error,
    checkedIds,
    verifiedIds,
    toggle,
    projects,
    reviews,
    loadProject,
    submitRepo,
    roleFit,
    openRoleSlug,
    setOpenRole: setOpenRoleSlug,
  };

  return <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>;
}

export function useAnalysis(): AnalysisContextValue {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysis must be used within AnalysisProvider");
  return ctx;
}
