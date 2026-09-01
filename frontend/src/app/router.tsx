import { createBrowserRouter, useNavigate } from "react-router-dom";
import { AnalyzingPage } from "@/features/analyzing/AnalyzingPage";
import { RoadmapPage } from "@/features/roadmap/RoadmapPage";
import { SetupPage } from "@/features/setup/SetupPage";
import { Resume } from "./Resume";

// The router owns the redirect to /analyzing — SetupPage itself only creates the
// student and stores the id (TDD §5.1).
function SetupRoute() {
  const navigate = useNavigate();
  return <SetupPage onComplete={() => navigate("/analyzing")} />;
}

export const router = createBrowserRouter([
  { path: "/", element: <Resume /> },
  { path: "/setup", element: <SetupRoute /> },
  { path: "/analyzing", element: <AnalyzingPage /> },
  { path: "/roadmap", element: <RoadmapPage /> },
]);
