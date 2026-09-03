import type { ReactNode } from "react";

interface AuthCardProps {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

// Shared centered-card layout for /login and /signup (PRD-V2 §4.1): dark backdrop, restrained
// brand presence, one card, one action. font-display marks the wordmark as the one place on
// this screen that gets the display face — everything else here is body text.
export function AuthCard({ title, children, footer }: AuthCardProps) {
  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <img src="/anchor-icon.svg" alt="" className="h-9 w-9 rounded-md" />
          <h1 className="font-display text-heading tracking-tight">ANCHOR</h1>
          <p className="text-sm text-muted-foreground">
            Course history + interests → 8 ranked roles, live.
          </p>
        </div>
        <div className="rounded-token-lg border bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">{title}</h2>
          {children}
        </div>
        {footer && <p className="text-center text-sm text-muted-foreground">{footer}</p>}
      </div>
    </div>
  );
}
