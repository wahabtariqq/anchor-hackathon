import { createBrowserRouter } from "react-router-dom";
import { LoginPage } from "@/features/auth/LoginPage";
import { SignupPage } from "@/features/auth/SignupPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { OnboardingRoute } from "@/features/onboarding/OnboardingRoute";
import { ProfilePage } from "@/features/profile/ProfilePage";
import { ProjectsPage } from "@/features/projects/ProjectsPage";
import { AnalysisProvider } from "@/features/roadmap/AnalysisContext";
import { RoadmapPage } from "@/features/roadmap/RoadmapPage";
import { SkillsPage } from "@/features/skills/SkillsPage";
import { AppShell } from "./AppShell";
import { RequireAuth } from "./RequireAuth";

// V2 route tree (docs/PRD-V2.md §3): /login, /signup unauthenticated; /onboarding authenticated
// but with NO sidebar (its own top-level route, not a child of AppShell); every other
// authenticated screen shares AppShell + one AnalysisProvider, lifted here from RoadmapPage
// (TDD-V2 §7.2) so /roadmap and /skills tick the same live state with zero refetch between them.
export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/signup", element: <SignupPage /> },
  {
    path: "/onboarding",
    element: (
      <RequireAuth>
        <OnboardingRoute />
      </RequireAuth>
    ),
  },
  {
    element: (
      <RequireAuth>
        <AnalysisProvider>
          <AppShell />
        </AnalysisProvider>
      </RequireAuth>
    ),
    children: [
      { path: "/", element: <DashboardPage />, handle: { title: "Dashboard" } },
      { path: "/roadmap", element: <RoadmapPage />, handle: { title: "Roadmap" } },
      { path: "/skills", element: <SkillsPage />, handle: { title: "Skills" } },
      { path: "/projects", element: <ProjectsPage />, handle: { title: "Projects" } },
      { path: "/profile", element: <ProfilePage />, handle: { title: "Profile" } },
    ],
  },
]);
