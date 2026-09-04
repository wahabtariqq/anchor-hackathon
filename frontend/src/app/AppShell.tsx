import { FolderKanban, LayoutDashboard, ListChecks, LogOut, Map } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getUser, logout } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/roadmap", label: "Roadmap", icon: Map, end: false },
  { to: "/skills", label: "Skills", icon: ListChecks, end: false },
  { to: "/projects", label: "Projects", icon: FolderKanban, end: false },
];

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-3 rounded-token-md border-l-2 border-transparent px-3 py-2.5 text-[15px] font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground motion-reduce:transition-none",
    isActive && "border-primary bg-primary/10 text-foreground",
  );

function initials(name: string): string {
  return (
    name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "?"
  );
}

// V2 app shell (docs/TDD-V2.md §7.2): 232px fixed sidebar, on every authenticated screen except
// /onboarding (PRD-V2 §3: "no sidebar" there — it stays outside this component). No topbar
// (removed per direct feedback — every screen already renders its own in-content heading, so a
// second "Dashboard"/"Roadmap"/… title bar was redundant). The account row at the bottom (avatar +
// name) is plain, non-interactive text — no /profile screen exists to link to (removed per direct
// feedback); the red log-out icon next to it is the only interactive element there.
export function AppShell() {
  const navigate = useNavigate();
  const user = getUser();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 flex w-[232px] flex-col border-r bg-card" aria-label="Primary">
        <div className="flex h-16 items-center gap-2.5 px-5">
          <img src="/anchor-icon.svg" alt="" className="h-9 w-auto" />
          <span className="font-display text-base font-semibold tracking-wide">ANCHOR</span>
        </div>
        <nav className="flex-1 space-y-0.5 px-3 py-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navLinkClass}>
              <Icon className="h-5 w-5" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-1 border-t p-3">
          <div className="flex min-w-0 flex-1 items-center gap-2 px-2 py-1.5 text-sm font-medium text-foreground">
            <Avatar className="h-7 w-7 shrink-0">
              <AvatarFallback className="text-xs font-medium">
                {user ? initials(user.name) : "?"}
              </AvatarFallback>
            </Avatar>
            <span className="truncate">{user?.name ?? "Account"}</span>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            aria-label="Log out"
            title="Log out"
            className="shrink-0 rounded-token-md p-2 text-anchor-critical transition-colors hover:bg-anchor-critical/10"
          >
            <LogOut className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </aside>

      <div className="min-w-0 flex-1 pl-[232px]">
        <Outlet />
      </div>
    </div>
  );
}
