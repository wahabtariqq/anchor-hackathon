import { useEffect, useRef, useState } from "react";
import type { RoadmapRole } from "@/lib/types";

interface WhatMovedProps {
  /** Core roles, stable (unsorted) order — same array RoadmapPage iterates for the re-sort. */
  roles: RoadmapRole[];
  roleFit: Map<string, number>;
  /** role.id -> current display position (0-indexed, best first). */
  pos: Map<string, number>;
}

const VISIBLE_MS = 3500;
const FADE_MS = 500;

export function WhatMoved({ roles, roleFit, pos }: WhatMovedProps) {
  const prev = useRef<{ fit: Map<string, number>; pos: Map<string, number> } | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const hideTimer = useRef<number>();
  const clearTimer = useRef<number>();

  useEffect(() => {
    if (prev.current) {
      let best: { title: string; dFit: number; fromFit: number; toFit: number; from: number; to: number } | null =
        null;
      for (const role of roles) {
        const fromFit = prev.current.fit.get(role.id) ?? 0;
        const toFit = roleFit.get(role.id) ?? 0;
        const dFit = toFit - fromFit;
        if (!best || Math.abs(dFit) > Math.abs(best.dFit)) {
          best = {
            title: role.title,
            dFit,
            fromFit,
            toFit,
            from: prev.current.pos.get(role.id) ?? 0,
            to: pos.get(role.id) ?? 0,
          };
        }
      }
      if (best && best.dFit !== 0) {
        const pct = `${best.fromFit}% → ${best.toFit}%`;
        const rank = best.from !== best.to ? ` · #${best.from + 1} → #${best.to + 1}` : "";
        window.clearTimeout(hideTimer.current);
        window.clearTimeout(clearTimer.current);
        setMessage(`${best.title} ${pct}${rank}`);
        setVisible(true);
        hideTimer.current = window.setTimeout(() => setVisible(false), VISIBLE_MS);
        clearTimer.current = window.setTimeout(() => setMessage(null), VISIBLE_MS + FADE_MS);
      }
    }
    prev.current = { fit: roleFit, pos };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleFit]);

  useEffect(
    () => () => {
      window.clearTimeout(hideTimer.current);
      window.clearTimeout(clearTimer.current);
    },
    [],
  );

  return (
    <>
      {message && (
        <p
          aria-hidden
          className="text-sm text-muted-foreground transition-opacity motion-reduce:transition-none"
          style={{ transitionDuration: `${FADE_MS}ms`, opacity: visible ? 1 : 0 }}
        >
          <span aria-hidden>▸ </span>
          {message}
        </p>
      )}
      <span className="sr-only" aria-live="polite">
        {visible ? message : ""}
      </span>
    </>
  );
}
