import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnalyzingPage } from "@/features/analyzing/AnalyzingPage";
import { SetupPage } from "@/features/setup/SetupPage";
import { setOnboarded } from "@/lib/auth";
import { StepHeader, type OnboardingStep } from "./StepHeader";

// Wraps the unmodified V1 AnalyzingPage, plus SetupPage split into two real steps, behind a
// 3-step header (PRD-V2 §4.2, redesigned per direct user feedback: Courses and Interests are
// separate steps with a Continue/Back transition, not one long scrolling form). Lives outside
// AppShell (no sidebar, per PRD-V2 §3) but still behind RequireAuth.
export function OnboardingRoute() {
  const navigate = useNavigate();
  const [step, setStep] = useState<OnboardingStep>("courses");

  return (
    <div>
      <StepHeader step={step} />
      {step === "analysis" ? (
        <AnalyzingPage
          onSuccess={() => {
            setOnboarded(true);
            navigate("/", { replace: true });
          }}
        />
      ) : (
        <SetupPage
          step={step}
          onContinue={() => setStep("interests")}
          onBack={() => setStep("courses")}
          onComplete={() => setStep("analysis")}
        />
      )}
    </div>
  );
}
