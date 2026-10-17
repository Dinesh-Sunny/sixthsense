import type { ModeMetrics } from "@/lib/api/types";
import { COPY } from "@/lib/copy";
import { cn } from "@/lib/utils";

const MAX_SQUARES = 12;

/** "4 of 6 came true" with one square per checked prediction: green yes, amber partly, outlined no. */
export function AccuracyMeter({ metrics, className, showLabel = true }: { metrics: ModeMetrics; className?: string; showLabel?: boolean }) {
  const { came_true_yes: yes, came_true_partly: partly, checked } = metrics;
  if (checked === 0) {
    return (
      <div className={cn("flex items-center gap-3", className)}>
        <span className="text-metric text-ink-muted">0 / 0</span>
        <span className="text-body-sm text-ink-muted">{COPY.scoreNothing}</span>
      </div>
    );
  }
  const squares = Array.from({ length: Math.min(checked, MAX_SQUARES) }, (_, n) =>
    n < yes ? "yes" : n < yes + partly ? "partly" : "no",
  );
  return (
    <div className={cn("flex items-center gap-3", className)} title={COPY.scoreTitle}>
      <span className="text-metric text-ink">
        {yes} of {checked}
      </span>
      <span className="flex gap-[3px]" aria-hidden>
        {squares.map((s, n) => (
          <i
            key={n}
            className={cn(
              "h-[22px] w-2.5 rounded-[3px]",
              s === "yes" && "bg-truth",
              s === "partly" && "bg-risk-mid",
              s === "no" && "bg-hairline shadow-[inset_0_0_0_1px_var(--ink-muted)]",
            )}
          />
        ))}
      </span>
      {showLabel && (
        <span className="text-body-sm text-ink">
          came true{partly > 0 ? ` · ${partly} partly` : ""}
        </span>
      )}
    </div>
  );
}
