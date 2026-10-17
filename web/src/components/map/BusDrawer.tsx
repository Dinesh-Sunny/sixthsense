"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ClipPlayer } from "@/components/ClipPlayer";
import { MAP_COPY } from "@/components/map/mapCopy";
import { StatusPill } from "@/components/StatusPill";
import { Button } from "@/components/ui/button";
import { alertsOptions, queryKeys, sendAlert } from "@/lib/api/queries";
import type { Incident, Pairing, Vehicle } from "@/lib/api/types";
import { BUS_COPY, BUS_STATE, VERDICT, busState, etaText, riskLabel, riskTone } from "@/lib/copy";
import { cn } from "@/lib/utils";

/** Selected bus: details scroll, actions stay pinned at the bottom. */
export function BusDrawer({
  busId,
  bus,
  pairing,
  incident,
  following,
  onFollow,
  onShowRoute,
  onBack,
}: {
  busId: string;
  bus: Vehicle | undefined;
  pairing: Pairing | undefined;
  incident: Incident | undefined;
  following: boolean;
  onFollow: () => void;
  onShowRoute: () => void;
  onBack: () => void;
}) {
  const queryClient = useQueryClient();
  const alerts = useQuery(alertsOptions());
  const nudge = useMutation({
    mutationFn: (incidentId: string) => sendAlert(incidentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.alerts }),
  });
  // "Driver nudged" ticks only once an alert for this moment is actually recorded.
  const nudged = Boolean(pairing && alerts.data?.some((a) => a.incident_id === pairing.incident_id)) || nudge.isSuccess;
  const state = busState(pairing);
  const checked = pairing ? pairing.came_true !== "unknown" : false;
  const done = [Boolean(pairing), nudged, Boolean(pairing), checked, checked];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4 [&>*]:shrink-0">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 self-start rounded-full text-data text-slate hover:text-ink focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <span aria-hidden>←</span> {BUS_COPY.needsLook}
        </button>
        {!bus ? (
          <p className="text-body-sm text-ink-muted">
            {BUS_COPY.busGone} <span className="font-mono">{busId}</span>
          </p>
        ) : (
          <>
            <div className="flex items-start gap-3">
              <div>
                <div className="font-serif text-[28px] leading-none">Route {bus.route}</div>
                <div className="mt-1 text-data text-ink-muted">{bus.id}</div>
              </div>
              <div className="flex-1" />
              <StatusPill tone={BUS_STATE[state].tone}>{BUS_STATE[state].label}</StatusPill>
            </div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-body-sm">
              <dt className="text-ink-muted">{BUS_COPY.towards}</dt>
              <dd>{bus.towards || "Not given"}</dd>
              <dt className="text-ink-muted">{BUS_COPY.nextStop}</dt>
              <dd>
                {bus.next_stop_name} · <span className="font-mono">{etaText(bus.eta_s)}</span>
              </dd>
            </dl>
            <button
              type="button"
              onClick={onShowRoute}
              className="self-start text-data text-slate underline-offset-2 hover:underline"
            >
              {BUS_COPY.showRoute} {bus.route} →
            </button>
          </>
        )}
        {pairing && incident && (
          <>
            <div className="overflow-hidden rounded-md bg-surface">
              <ClipPlayer
                source={incident.source}
                controls
                label="Stand-in clip for this bus"
                fallbackLabel={BUS_COPY.standIn}
                overlay={<StatusPill tone="sample">{BUS_COPY.standIn}</StatusPill>}
              />
            </div>
            <div className="text-eye">Next</div>
            <p className="font-serif text-xl leading-[1.2] text-balance">{incident.what_next}</p>
            {incident.why && (
              <p className="text-body-sm text-ink-muted">
                <b className="font-medium text-ink">{MAP_COPY.why}</b> {incident.why}
              </p>
            )}
            {incident.fix && (
              <p className="text-body-sm text-ink-muted">
                <b className="font-medium text-ink">{MAP_COPY.fix}</b> {incident.fix}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <StatusPill tone={riskTone(pairing.risk)}>{riskLabel(pairing.risk)}</StatusPill>
              <StatusPill tone={VERDICT[pairing.came_true].tone}>{VERDICT[pairing.came_true].label}</StatusPill>
            </div>
            <ol className="flex flex-col gap-1.5" aria-label="What happened so far">
              {BUS_COPY.timeline.map((step, n) => (
                <li key={step} className={cn("flex items-center gap-2 text-body-sm", !done[n] && "text-ink-muted")}>
                  <span aria-hidden className={cn("size-2 rounded-full", done[n] ? "bg-truth" : "border border-ink-muted")} />
                  {step}
                  <span className="sr-only">{done[n] ? " (done)" : " (not yet)"}</span>
                </li>
              ))}
            </ol>
          </>
        )}
      </div>

      <div className="flex flex-col gap-2 border-t border-hairline px-4 py-3">
        <div className="flex flex-wrap gap-2">
          {pairing && (
            <Button size="sm" onClick={() => nudge.mutate(pairing.incident_id)} disabled={nudged || nudge.isPending}>
              {nudge.isPending ? MAP_COPY.nudging : nudged ? MAP_COPY.nudged : MAP_COPY.nudge}
            </Button>
          )}
          {pairing && (
            <Button asChild size="sm" variant="outline">
              <Link href={{ pathname: "/incident", query: { id: pairing.incident_id } }}>{BUS_COPY.openReport}</Link>
            </Button>
          )}
          {bus && (
            <Button size="sm" variant="outline" onClick={onFollow} aria-pressed={following}>
              {following ? BUS_COPY.following : BUS_COPY.follow}
            </Button>
          )}
        </div>
        {nudge.isError && <p className="text-body-sm text-risk-high">{MAP_COPY.nudgeFailed}</p>}
        {pairing && !nudged && !nudge.isError && <p className="text-data text-ink-muted">{MAP_COPY.nudgeNote}</p>}
      </div>
    </div>
  );
}
