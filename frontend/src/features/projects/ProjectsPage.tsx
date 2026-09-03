import { useEffect, useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalysis } from "@/features/roadmap/AnalysisContext";
import { getProjects } from "@/lib/api";
import type { ProjectWithHistory } from "@/lib/types";
import { ProjectCard } from "./ProjectCard";

export function ProjectsPage() {
  const { data } = useAnalysis();
  const [items, setItems] = useState<ProjectWithHistory[] | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getProjects().then((res) => {
      if (!cancelled) setItems(res.projects);
    });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const rolesById = useMemo(() => new Map((data?.roles ?? []).map((r) => [r.id, r])), [data]);
  const skillsById = useMemo(() => new Map((data?.skills ?? []).map((s) => [s.id, s])), [data]);

  if (!items) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 p-8">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-8">
      <header className="space-y-1">
        <h1 className="font-display text-heading">Projects</h1>
        <p className="text-sm text-muted-foreground">
          Every project ANCHOR designed for you, and every repo you've submitted against it.
        </p>
      </header>

      {items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          Projects appear when you open Prove It on a role.
        </p>
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const role = rolesById.get(item.project.role_id);
            if (!role) return null;
            return (
              <ProjectCard
                key={item.project.id}
                item={item}
                role={role}
                skillsById={skillsById}
                onResubmitted={() => setReloadKey((k) => k + 1)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
