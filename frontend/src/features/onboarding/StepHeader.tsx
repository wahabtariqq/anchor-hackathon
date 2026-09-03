import { cn } from "@/lib/utils";

export type OnboardingStep = "courses" | "interests" | "analysis";

const STEPS: { key: OnboardingStep; label: string }[] = [
  { key: "courses", label: "Courses" },
  { key: "interests", label: "Interests" },
  { key: "analysis", label: "Analysis" },
];

// The same order as this list (Courses -> Interests -> Analysis) is a display grouping only —
// SetupPage itself renders courses and interests as one continuous form (PRD-V2 §4.2 changes no
// behavior), so "interests" never lights up as active on its own; it and "courses" both read as
// the current step while step === "setup".
export function StepHeader({ step }: { step: OnboardingStep }) {
  return (
    <ol className="mx-auto flex max-w-4xl items-center gap-3 px-8 pt-8 text-sm">
      {STEPS.map((s, i) => {
        const isDone =
          (step === "interests" && s.key === "courses") ||
          (step === "analysis" && s.key !== "analysis");
        const isActive = s.key === step || (step === "interests" && s.key === "courses");
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
                  isActive && !isDone && "border-foreground",
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
