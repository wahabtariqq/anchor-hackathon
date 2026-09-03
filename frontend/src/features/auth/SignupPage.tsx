import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthError, isOnboarded, signup } from "@/lib/auth";
import { AuthCard } from "./AuthCard";

const MIN_PASSWORD_CHARS = 8;

export function SignupPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [semester, setSemester] = useState("4");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const semesterNumber = Number(semester);
  const semesterValid = Number.isInteger(semesterNumber) && semesterNumber >= 1 && semesterNumber <= 12;
  const passwordValid = password.length >= MIN_PASSWORD_CHARS;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (submitting) return;
    if (!name.trim()) {
      setError("Enter your name.");
      return;
    }
    if (!semesterValid) {
      setError("Semester must be a number between 1 and 12.");
      return;
    }
    if (!passwordValid) {
      setError(`Password must be at least ${MIN_PASSWORD_CHARS} characters.`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await signup({ email, password, name: name.trim(), semester: semesterNumber });
      // Claim-on-signup may have already attached an existing analysis (TDD-V2 §5.1) — land on
      // the Dashboard for that case, /onboarding otherwise.
      navigate(isOnboarded() ? "/" : "/onboarding", { replace: true });
    } catch (err) {
      setError(err instanceof AuthError ? err.message : "Couldn't create your account — try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle="Create your account to get your personalized roadmap."
      footer={
        <>
          Already have one?{" "}
          <Link to="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-[1fr_6rem] gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="name">Your name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="semester">Semester</Label>
            <Input
              id="semester"
              inputMode="numeric"
              value={semester}
              onChange={(e) => setSemester(e.target.value)}
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-xs text-anchor-critical">{error}</p>}
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthCard>
  );
}
