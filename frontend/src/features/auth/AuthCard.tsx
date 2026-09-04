import type { ReactNode } from "react";

interface AuthCardProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}

// Shared centered-card layout for /login and /signup (PRD-V2 §4.1): a big logo above a raised
// card, restrained brand presence, one action. A faint grid + soft blue glow behind everything
// gives the first screen a bit of depth instead of sitting flat on the base surface.
export function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background p-8">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(hsl(var(--border) / 0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border) / 0.5) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
          maskImage: "radial-gradient(ellipse 60% 50% at 50% 40%, black 0%, transparent 75%)",
          WebkitMaskImage: "radial-gradient(ellipse 60% 50% at 50% 40%, black 0%, transparent 75%)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-[8%] h-[420px] w-[640px] -translate-x-1/2 rounded-full bg-primary/25 blur-[110px]"
      />

      <div className="relative w-full max-w-sm space-y-8">
        <div className="flex justify-center">
          <img src="/anchor-logo.svg" alt="ANCHOR" className="h-12 w-auto sm:h-14" />
        </div>
        <div className="rounded-token-lg border bg-card p-8 shadow-2xl shadow-black/40">
          <h2 className="text-2xl font-semibold">{title}</h2>
          <p className="mt-1 text-base text-muted-foreground">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
        {footer && <p className="text-center text-sm text-muted-foreground">{footer}</p>}
      </div>
    </div>
  );
}
