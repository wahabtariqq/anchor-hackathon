import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { analyze, ApiError } from "@/lib/api";

// Staged copy is fully decoupled from the request promise (TDD §7.6) — the request can
// finish before, during, or long after any of these lines show.
const STAGES = [
  { at: 0, text: "Reading your transcript…" },
  { at: 12_000, text: "Mapping courses to skills…" },
  { at: 28_000, text: "Matching roles to your interests…" },
  { at: 45_000, text: "Finding the paths worth considering…" },
  { at: 70_000, text: "Writing your roadmap…" },
];

export function AnalyzingPage() {
  const navigate = useNavigate();
  const [stageIndex, setStageIndex] = useState(0);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  // POST /api/analyze must fire exactly once per attempt — React 18 StrictMode's dev-only
  // double-invoke of effects would otherwise fire it twice for the same student.
  const firedFor = useRef<number | null>(null);

  useEffect(() => {
    setStageIndex(0);
    const timers = STAGES.slice(1).map((s, i) => window.setTimeout(() => setStageIndex(i + 1), s.at));
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [attempt]);

  useEffect(() => {
    if (firedFor.current === attempt) return;
    firedFor.current = attempt;
    setFailed(false);

    // Re-check firedFor (not a per-invocation closure flag) before acting on the
    // result: StrictMode's dev-only double-invoke cleans up this same effect run
    // immediately after starting the fetch, so a closure-local "cancelled" would
    // wrongly suppress the one real request's own result.
    analyze()
      .then(() => {
        if (firedFor.current === attempt) navigate("/roadmap", { replace: true });
      })
      .catch((err: unknown) => {
        if (firedFor.current !== attempt) return;
        // 409 = analysis already exists (e.g. a reload landed here again) — not a failure.
        if (err instanceof ApiError && err.status === 409) {
          navigate("/roadmap", { replace: true });
          return;
        }
        setFailed(true);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt]);

  if (failed) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
        <p className="text-lg font-medium">That took longer than expected.</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          The analysis didn't come back in time. Nothing was lost — try again.
        </p>
        <Button onClick={() => setAttempt((a) => a + 1)}>Try again</Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-8 text-center">
      <p className="text-lg font-medium">{STAGES[stageIndex].text}</p>
      <p className="text-sm text-muted-foreground">This takes a minute — we're reading every course.</p>
    </div>
  );
}
