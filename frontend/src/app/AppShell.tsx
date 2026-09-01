import { Link, Outlet, useLocation } from "react-router-dom";
import { getStudentName } from "@/lib/identity";

// The one persistent piece of chrome across all three screens (Setup/Analyzing/Roadmap
// — PRD §10 mandates exactly these three, no new pages). Branding only: a wordmark and,
// once known, the student's name for a personalized feel. No nav links, no settings, no
// login — there is nothing else in scope to navigate to.
export function AppShell() {
  // Re-render on navigation so a just-completed Setup (or a "Start over" clear)
  // is reflected immediately — AppShell itself never reads student state otherwise.
  useLocation();
  const name = getStudentName();

  return (
    <div className="min-h-screen">
      <header className="flex h-12 items-center justify-between border-b px-6">
        <Link to="/" className="flex items-center gap-2 text-sm font-semibold tracking-wide">
          <img src="/anchor-icon.svg" alt="" className="h-6 w-6 rounded-md" />
          ANCHOR
        </Link>
        {name && <span className="text-sm text-muted-foreground">{name}</span>}
      </header>
      <Outlet />
    </div>
  );
}
