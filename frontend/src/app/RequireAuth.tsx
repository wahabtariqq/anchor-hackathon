import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getToken, isOnboarded } from "@/lib/auth";

// TDD-V2 §5.5's resume rule: no token -> /login; token but no analysis yet -> /onboarding
// (simulating the real backend's current_student 404). Replaces app/Resume.tsx, whose job this
// now is.
export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();

  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  if (!isOnboarded() && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }
  return <>{children}</>;
}
