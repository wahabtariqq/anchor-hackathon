import { cn } from "@/lib/utils";

export type OnboardingStep = "courses" | "interests" | "analysis";

const STEPS: { key: OnboardingStep; label: string }[] = [
  { key: "courses", label: "Courses" },
  { key: "interests", label: "Interests" },
  { key: "analysis", label: "Analysis" },
];

const ORDER: Record<OnboardingStep, number> = { courses: 0, interests: 1, analysis: 2 };

export function StepHeader({ step }: { step: OnboardingStep }) {
  const current = ORDER[step];
  return (
    <ol className="mx-auto flex max-w-4xl items-center gap-3 px-8 pt-8 text-sm">
      {STEPS.map((s, i) => {
        const isDone = ORDER[s.key] < current;
        const isActive = s.key === step;
        return (
          <li key={s.key} className="flex items-center gap-3">
            {i > 0 && <span className="h-px w-8 bg-border" aria-hidden />}
            <span
              className={cn(
                "flex items-center gap-2 font-medium",
                isDone || isActive ? "text-foreground" : "text-muted-foreground",
              )}
            >
              <span
                className={cn(
                  "flex h-5 w-5 items-center justify-center rounded-full border text-xs",
                  isDone && "border-anchor-good bg-anchor-good/10 text-anchor-good",
                  isActive && !isDone && "border-primary bg-primary/10 text-primary",
                )}
              >
                {i + 1}
              </span>
              {s.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
