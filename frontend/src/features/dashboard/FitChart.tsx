import { useMemo } from "react";
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

const WIDTH = 480;
const HEIGHT = 160;
const PAD_X = 8;
const PAD_Y = 12;

// Inline SVG polyline, no charting library — same approach FitRing already proves out
// (docs/TDD-V2.md §7.3). A legend with direct value labels stands in for per-point tooltips;
// a visually-hidden summary gives the trend a text alternative (identity is never color-alone).
export function FitChart({ series }: { series: FitChartSeries[] }) {
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
    return PAD_X + ratio * (WIDTH - PAD_X * 2);
  }
  function y(fit: number): number {
    return HEIGHT - PAD_Y - (fit / 100) * (HEIGHT - PAD_Y * 2);
  }

  if (withPoints.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-token-lg border border-dashed text-center text-sm text-muted-foreground">
        Your progress will chart here — tick a skill or submit a project.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" className="h-40 w-full" aria-hidden>
        <line
          x1={PAD_X}
          y1={HEIGHT - PAD_Y}
          x2={WIDTH - PAD_X}
          y2={HEIGHT - PAD_Y}
          className="stroke-border"
          strokeWidth={1}
        />
        {withPoints.map((s, i) => {
          const d = s.points.map((p, pi) => `${pi === 0 ? "M" : "L"} ${x(p.at)} ${y(p.fit)}`).join(" ");
          const last = s.points[s.points.length - 1];
          return (
            <g key={s.roleId}>
              <path
                d={d}
                fill="none"
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx={x(last.at)} cy={y(last.fit)} r={3} fill={COLORS[i % COLORS.length]} />
            </g>
          );
        })}
      </svg>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {withPoints.map((s, i) => (
          <li key={s.roleId} className="flex items-center gap-1.5">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: COLORS[i % COLORS.length] }}
              aria-hidden
            />
            {s.title} · {s.points[s.points.length - 1].fit}%
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
