import type { Incident } from "@/lib/api/types";

/**
 * The one place pipeline words may appear on screen (DESIGN.md): how the
 * moment was found, verified and checked, for people who want the details.
 */
export function HowItDecided({ incident: i }: { incident: Incident }) {
  const rows: [string, string][] = [
    ["Search query", i.query ?? ""],
    ["Search match", i.similarity != null ? i.similarity.toFixed(2) : ""],
    ["Kind of moment", i.type],
    ["Verified by", i.verify_by],
    ["Verify score", i.verify_score.toFixed(2)],
    ["Verify note", i.verify_note],
    ["Self-check evidence", i.came_true_evidence],
    ["Judged by", i.judged_by ?? ""],
    ["Next segment", i.next_source ?? ""],
    ["Source segment", i.source ?? "none"],
    ["Run", i.run_id ?? "none"],
  ];
  return (
    <div className="flex flex-col gap-2 rounded-sm border border-hairline bg-surface p-3">
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-data">
        {rows
          .filter(([, v]) => v)
          .map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-ink-muted">{k}</dt>
              <dd className="break-all text-ink">{v}</dd>
            </div>
          ))}
      </dl>
      {i.trace_url && (
        <a href={i.trace_url} target="_blank" rel="noreferrer" className="text-data text-slate underline-offset-2 hover:underline">
          Open the Weave trace →
        </a>
      )}
    </div>
  );
}
