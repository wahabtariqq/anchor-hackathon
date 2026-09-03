import { useEffect, useMemo, useRef, useState } from "react";
import type { SnapshotPoint } from "@/lib/types";

interface FitChartSeries {
  roleId: string;
  title: string;
  points: SnapshotPoint[];
}

// dataviz skill's categorical palette, slots 1-3 (dark-mode steps — this app is dark-only):
// blue / orange / aqua. Slot 1 intentionally matches --anchor-ring-fill's hue so the top role's
// line reads as the same accent used for its fit ring elsewhere.
const COLORS = ["#3987e5", "#d95926", "#199e70"];

const HEIGHT = 220;
const PAD_L = 34;
const PAD_R = 10;
const PAD_TOP = 14;
const PAD_BOTTOM = 12;
const GRID_STEPS = [0, 25, 50, 75, 100];

// Inline SVG, no charting library — same approach FitRing already proves out (docs/TDD-V2.md
// §7.3). Gridlines + a soft gradient fill under each line give it real visual weight instead of
// three flat strokes floating in empty space; a legend with direct value labels stands in for
// per-point tooltips, and a visually-hidden summary gives the trend a text alternative.
//
// The SVG's viewBox is set to the container's MEASURED pixel width (ResizeObserver), not a
// fixed constant scaled up via preserveAspectRatio="none" — that non-uniform scaling stretched
// everything horizontally by ~2x (a 480-unit viewBox filling a ~1050px container), turning round
// markers into ellipses and text into visibly warped glyphs, which is what read as "looks like a
// picture" instead of crisp vector UI. With viewBox width == rendered width, one SVG unit is
// exactly one CSS pixel in both axes, so nothing scales unevenly.
export function FitChart({ series }: { series: FitChartSeries[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(480);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) setWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const withPoints = series.filter((s) => s.points.length > 0);

  const { minAt, maxAt } = useMemo(() => {
    const times = withPoints.flatMap((s) => s.points.map((p) => new Date(p.at).getTime()));
    if (times.length === 0) return { minAt: 0, maxAt: 1 };
    const min = Math.min(...times);
    const max = Math.max(...times);
    return { minAt: min, maxAt: max === min ? min + 1 : max };
  }, [withPoints]);

  function x(at: string): number {
    const ratio = (new Date(at).getTime() - minAt) / (maxAt - minAt);
    return PAD_L + ratio * (width - PAD_L - PAD_R);
  }
  function y(fit: number): number {
    return PAD_TOP + (1 - fit / 100) * (HEIGHT - PAD_TOP - PAD_BOTTOM);
  }

  if (withPoints.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center rounded-token-lg border border-dashed bg-card/40 text-center text-sm text-muted-foreground">
        Your progress will chart here — tick a skill or submit a project.
      </div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-4 rounded-token-lg border bg-card p-4">
      <svg width={width} height={HEIGHT} viewBox={`0 0 ${width} ${HEIGHT}`} className="block" aria-hidden>
        <defs>
          {withPoints.map((s, i) => (
            <linearGradient key={s.roleId} id={`fit-grad-${s.roleId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.38} />
              <stop offset="100%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>

        {/* Gridlines + % labels — turns "three lines in empty space" into a readable scale. */}
        {GRID_STEPS.map((pct) => (
          <g key={pct}>
            <line
              x1={PAD_L}
              y1={y(pct)}
              x2={width - PAD_R}
              y2={y(pct)}
              className={pct === 0 ? "stroke-border" : "stroke-border/50"}
              strokeWidth={1}
            />
            <text x={PAD_L - 8} y={y(pct)} textAnchor="end" dominantBaseline="middle" className="fill-muted-foreground text-[9px]">
              {pct}%
            </text>
          </g>
        ))}

        {withPoints.map((s, i) => {
          const color = COLORS[i % COLORS.length];
          const line = s.points.map((p, pi) => `${pi === 0 ? "M" : "L"} ${x(p.at)} ${y(p.fit)}`).join(" ");
          // The fill hugs the line at a fixed depth rather than washing down to the 0% baseline —
          // with three lines often sitting close together, a full-height fill overlaps into a
          // muddy blend; a short "glow" underneath each line stays legible per series.
          const FILL_DEPTH = 34;
          const back = [...s.points].reverse().map((p) => `L ${x(p.at)} ${y(p.fit) + FILL_DEPTH}`).join(" ");
          const area = `${line} ${back} Z`;
          const last = s.points[s.points.length - 1];
          return (
            <g key={s.roleId}>
              <path d={area} fill={`url(#fit-grad-${s.roleId})`} stroke="none" />
              <path d={line} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
              {/* soft outer ring behind the solid marker, for a bit of glow on the current value */}
              <circle cx={x(last.at)} cy={y(last.fit)} r={7} fill={color} opacity={0.25} />
              <circle cx={x(last.at)} cy={y(last.fit)} r={3.5} fill={color} stroke="hsl(var(--card))" strokeWidth={1.5} />
            </g>
          );
        })}
      </svg>
      <ul className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
        {withPoints.map((s, i) => (
          <li key={s.roleId} className="flex items-center gap-1.5">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: COLORS[i % COLORS.length] }}
              aria-hidden
            />
            <span className="text-foreground">{s.title}</span> · {s.points[s.points.length - 1].fit}%
          </li>
        ))}
      </ul>
      <p className="sr-only">
        {withPoints
          .map((s) => `${s.title}: ${s.points[0].fit}% to ${s.points[s.points.length - 1].fit}%`)
          .join(". ")}
      </p>
    </div>
  );
}
