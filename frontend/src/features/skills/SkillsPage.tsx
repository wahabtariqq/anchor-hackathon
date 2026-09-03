import { Check } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAnalysis } from "@/features/roadmap/AnalysisContext";
import { skillState, type SkillState } from "@/features/roadmap/SkillRow";
import { getSkills } from "@/lib/api";
import type { SkillInventoryRow } from "@/lib/types";
import { StatusPill } from "./StatusPill";

const FILTERS: { key: SkillState | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "verified", label: "Verified" },
  { key: "ticked", label: "Learned" },
  { key: "covered-full", label: "Covered" },
  { key: "covered-partial", label: "Partial" },
  { key: "missing", label: "Missing" },
];

// The screen that makes "skills are the source of truth" visible — one row, many roles
// (PRD-V2 §4.5). Ticking here reuses AnalysisContext's exact optimistic path RoleDrawer uses
// (toggle()), so a tick made here shows up on /roadmap with zero refetch, and vice versa.
export function SkillsPage() {
  const { data, checkedIds, verifiedIds, toggle } = useAnalysis();
  const [rows, setRows] = useState<SkillInventoryRow[] | null>(null);
  const [filter, setFilter] = useState<SkillState | "all">("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    getSkills().then((res) => {
      if (!cancelled) setRows(res.skills);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const roleSlugById = useMemo(() => new Map((data?.roles ?? []).map((r) => [r.id, r.slug])), [data]);

  // rows' own checked/verified are a load-time snapshot — overlay the live sets, same reason
  // RoadmapPage's skillsById does (AnalysisContext seeds them once; only the sets are live).
  const live = useMemo(
    () => (rows ?? []).map((s) => ({ ...s, checked: checkedIds.has(s.id), verified: verifiedIds.has(s.id) })),
    [rows, checkedIds, verifiedIds],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return live.filter((s) => {
      if (filter !== "all" && skillState(s) !== filter) return false;
      if (q && !s.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [live, filter, query]);

  if (!rows) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-8">
        <Skeleton className="h-9 w-full" />
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-8">
      <header className="space-y-1">
        <h1 className="font-display text-heading">Skills</h1>
        <p className="text-sm text-muted-foreground">
          Every skill ANCHOR knows about you — one row, every role that needs it.
        </p>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={filter} onValueChange={(v) => setFilter(v as SkillState | "all")}>
          <TabsList>
            {FILTERS.map((f) => (
              <TabsTrigger key={f.key} value={f.key}>
                {f.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <Input
          placeholder="Search skills…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">No skills match.</p>
      ) : (
        <div className="divide-y rounded-token-lg border">
          {filtered.map((s) => {
            const state = skillState(s);
            const inputId = `skills-${s.id}`;
            return (
              <div key={s.id} className="flex items-start gap-4 p-4">
                <div className="flex h-5 w-5 shrink-0 items-center justify-center pt-0.5">
                  {state === "verified" ? (
                    <Check className="h-4 w-4 text-anchor-good" aria-hidden />
                  ) : state === "covered-partial" ? (
                    <span
                      aria-hidden
                      className="h-3 w-3 rounded-full border-2 border-muted-foreground/50"
                      style={{
                        background: "linear-gradient(90deg, hsl(var(--muted-foreground)) 50%, transparent 50%)",
                      }}
                    />
                  ) : (
                    // covered-full falls through to here too — checked, matching SkillRow.tsx.
                    <Checkbox
                      id={inputId}
                      checked={state === "ticked" || state === "covered-full"}
                      onCheckedChange={() => toggle(s.id)}
                    />
                  )}
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Label htmlFor={inputId} className="text-sm font-semibold">
                      {s.name}
                    </Label>
                    <StatusPill skill={s} />
                  </div>
                  <p className="text-sm text-muted-foreground">{s.real_world}</p>
                  {s.roles.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {s.roles.map((r) => (
                        <Link key={r.id} to={`/roadmap?role=${roleSlugById.get(r.id) ?? ""}`}>
                          <Badge
                            variant="outline"
                            className="text-xs font-normal transition-colors hover:border-foreground/40 hover:text-foreground"
                          >
                            {r.title}
                          </Badge>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
