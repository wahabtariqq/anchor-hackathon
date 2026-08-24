import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { RoadmapPage } from "./features/roadmap/RoadmapPage";

// TEMPORARY Day 1 entry point — renders RoadmapPage directly so it's visually
// verifiable before router.tsx/App.tsx/Resume.tsx exist. Replaced on Day 5
// with the real <App /> (providers) + <RouterProvider /> (3 routes).
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RoadmapPage />
  </StrictMode>,
);
