import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getRoadmap, setProgress } from "@/lib/api";
import { fitPercent } from "@/lib/scoring";
import type { RoadmapResponse } from "@/lib/types";

interface AnalysisContextValue {
  data: RoadmapResponse | null;
  loading: boolean;
  error: string | null;
  checkedIds: Set<string>;
  verifiedIds: Set<string>;
  toggle: (skillId: string) => void;
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
  const [openRoleSlug, setOpenRoleSlug] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getRoadmap()
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setCheckedIds(new Set(res.skills.filter((s) => s.checked).map((s) => s.id)));
        setVerifiedIds(new Set(res.skills.filter((s) => s.verified).map((s) => s.id)));
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

  function toggle(skillId: string) {
    const wasChecked = checkedIds.has(skillId);

    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (wasChecked) next.delete(skillId);
      else next.add(skillId);
      return next;
    });

    // Fire-and-forget: nothing awaits the network, the visual update is already committed above.
    setProgress({ skill_id: skillId, checked: !wasChecked }).catch(() => {
      setCheckedIds((cur) => {
        const reverted = new Set(cur);
        if (wasChecked) reverted.add(skillId);
        else reverted.delete(skillId);
        return reverted;
      });
      // TODO (Day 3): surface a sonner toast here on revert.
    });
  }

  const value: AnalysisContextValue = {
    data,
    loading,
    error,
    checkedIds,
    verifiedIds,
    toggle,
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
