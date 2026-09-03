import { cn } from "@/lib/utils";

interface FitRingProps {
  percent: number;
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
  labelClassName?: string;
  className?: string;
}

export function FitRing({
  percent,
  size = 56,
  strokeWidth = 5,
  showLabel = true,
  labelClassName,
  className,
}: FitRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, percent));
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center shrink-0", className)}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          className="fill-none stroke-anchor-ring-track"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="fill-none stroke-anchor-ring-fill transition-[stroke-dashoffset] duration-500 ease-out motion-reduce:transition-none"
        />
      </svg>
      {showLabel && (
        <span className={cn("absolute font-display text-sm font-semibold", labelClassName)}>{clamped}%</span>
      )}
    </div>
  );
}
