import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnalyzingPage } from "@/features/analyzing/AnalyzingPage";
import { SetupPage } from "@/features/setup/SetupPage";
import { setOnboarded } from "@/lib/auth";
import { StepHeader, type OnboardingStep } from "./StepHeader";

// Wraps the unmodified V1 Setup + Analyzing flow behind a 3-step header (PRD-V2 §4.2) — neither
// component's own behavior changes, only what's drawn around them. Lives outside AppShell (no
// sidebar, per PRD-V2 §3) but still behind RequireAuth.
export function OnboardingRoute() {
  const navigate = useNavigate();
  const [step, setStep] = useState<OnboardingStep>("courses");

  return (
    <div>
      <StepHeader step={step} />
      {step === "courses" ? (
        <SetupPage onComplete={() => setStep("analysis")} />
      ) : (
        <AnalyzingPage
          onSuccess={() => {
            setOnboarded(true);
            navigate("/", { replace: true });
          }}
        />
      )}
    </div>
  );
}
