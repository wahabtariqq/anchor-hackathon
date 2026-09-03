import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useAnalysis } from "@/features/roadmap/AnalysisContext";
import { getUser, logout, logoutAll } from "@/lib/auth";

function formatDate(at: string): string {
  return new Date(at).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

// Read-only account info + the analysed course/interest snapshot (PRD-V2 §4.7) — no editing;
// re-onboarding to change courses/interests is out of scope (PRD-V2 §2 non-goals).
export function ProfilePage() {
  const navigate = useNavigate();
  const { data } = useAnalysis();
  const user = getUser();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  async function handleLogoutAll() {
    await logoutAll();
    navigate("/login", { replace: true });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-8">
      <header>
        <h1 className="font-display text-heading">Profile</h1>
      </header>

      <Card>
        <CardContent className="grid grid-cols-2 gap-4 p-5 text-sm">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Name</p>
            <p className="mt-0.5 font-medium">{user?.name ?? data?.student.name ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Email</p>
            <p className="mt-0.5 font-medium">{user?.email ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Semester</p>
            <p className="mt-0.5 font-medium">{user?.semester ?? data?.student.semester ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Account created</p>
            <p className="mt-0.5 font-medium">{user ? formatDate(user.created_at) : "—"}</p>
          </div>
        </CardContent>
      </Card>

      {data && (
        <Card>
          <CardContent className="space-y-4 p-5">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Analysed courses
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {data.courses.map((c) => (
                  <Badge key={c.id} variant="outline" className="text-xs font-normal">
                    {c.code} · {c.name}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Interests</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {data.student.interests.map((i) => (
                  <Badge key={i} variant="outline" className="text-xs font-normal">
                    {i}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="space-y-3 p-5">
          <div>
            <p className="text-sm font-medium">Password</p>
            <p className="text-sm text-muted-foreground">Reset isn't self-serve yet — contact us.</p>
          </div>
          <Separator />
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={handleLogout}>
              Log out
            </Button>
            <Button variant="outline" onClick={handleLogoutAll}>
              Log out everywhere
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
