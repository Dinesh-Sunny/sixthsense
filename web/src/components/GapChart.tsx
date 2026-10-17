import type { GapPoint } from "@/lib/api/types";
import { CLOSE_CL, gapSummary } from "@/lib/copy";

const W = 600;
const H = 120;
const X0 = 40;
const X1 = 590;
const Y0 = 20;
const Y1 = 100;

/** Gap between the two road users over the clip, with the close-call line. */
export function GapChart({ series }: { series: GapPoint[] }) {
  const g = gapSummary(series);
  if (series.length < 2 || !g) return null;
  const t0 = series[0].t;
  const tSpan = Math.max(series[series.length - 1].t - t0, 0.001);
  const maxCl = Math.max(CLOSE_CL * 1.2, ...series.map((p) => p.cl));
  const x = (t: number) => X0 + ((t - t0) / tSpan) * (X1 - X0);
  const y = (cl: number) => Y1 - (cl / maxCl) * (Y1 - Y0);
  const low = series.reduce((a, b) => (b.cl < a.cl ? b : a), series[0]);
  const points = series.map((p) => `${x(p.t).toFixed(1)},${y(p.cl).toFixed(1)}`).join(" ");
  const label = `Gap falls from ${g.from.toFixed(1)} to ${g.to.toFixed(1)} car lengths over ${g.seconds.toFixed(1)} seconds`;
  const lowX = Math.min(x(low.t), X1 - 90);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={label} className="font-mono">
      <line x1={X0} y1={Y1} x2={X1} y2={Y1} stroke="var(--hairline)" />
      <line x1={X0} y1={y(CLOSE_CL)} x2={X1} y2={y(CLOSE_CL)} stroke="var(--risk-high)" strokeDasharray="4 4" />
      <text x={X1 + 2} y={y(CLOSE_CL) - 4} fontSize="11" fill="var(--risk-high)" textAnchor="end">
        {CLOSE_CL} cl threshold
      </text>
      <polyline fill="none" stroke="var(--ink)" strokeWidth="2" points={points} />
      <circle cx={x(low.t)} cy={y(low.cl)} r="4" fill="var(--risk-high)" />
      <text x={X0} y={14} fontSize="11" fill="var(--ink-muted)">
        {g.from.toFixed(1)} cl
      </text>
      <text x={lowX} y={H - 6} fontSize="11" fill="var(--ink-muted)">
        {g.to.toFixed(1)} cl at {g.seconds.toFixed(1)}s
      </text>
    </svg>
  );
}
