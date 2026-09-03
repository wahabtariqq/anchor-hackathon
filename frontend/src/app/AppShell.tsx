import { FolderKanban, LayoutDashboard, ListChecks, Map, User } from "lucide-react";
import { NavLink, Outlet, useMatches, useNavigate } from "react-router-dom";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
    "flex items-center gap-2.5 rounded-token-md border-l-2 border-transparent px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground motion-reduce:transition-none",
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

// V2 app shell (docs/TDD-V2.md §7.2): 232px fixed sidebar + topbar, on every authenticated
// screen except /onboarding (PRD-V2 §3: "no sidebar" there — it stays outside this component).
// Replaces the V1 top-bar-only shell; that shell's "no nav links" comment described V1 scope,
// not a constraint that outlives it.
export function AppShell() {
  const navigate = useNavigate();
  const matches = useMatches();
  const user = getUser();

  const title =
    [...matches].reverse().find((m) => (m.handle as { title?: string } | undefined)?.title)
      ?.handle as { title?: string } | undefined;

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 flex w-[232px] flex-col border-r bg-card" aria-label="Primary">
        <div className="flex h-14 items-center gap-2 px-5">
          <img src="/anchor-icon.svg" alt="" className="h-6 w-auto" />
          <span className="font-display text-sm font-semibold tracking-wide">ANCHOR</span>
        </div>
        <nav className="flex-1 space-y-0.5 px-3 py-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navLinkClass}>
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t p-3">
          <NavLink to="/profile" className={navLinkClass}>
            <User className="h-4 w-4" aria-hidden />
            Profile
          </NavLink>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col pl-[232px]">
        <header className="flex h-14 shrink-0 items-center justify-between border-b px-6">
          <h1 className="text-sm font-semibold">{title?.title ?? "ANCHOR"}</h1>
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-2 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs font-medium">
                  {user ? initials(user.name) : "?"}
                </AvatarFallback>
              </Avatar>
              {user && <span className="text-sm text-muted-foreground">{user.name}</span>}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => navigate("/profile")}>Profile</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>Log out</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
