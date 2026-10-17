"use client";

import { useQuery } from "@tanstack/react-query";
import { Panel, PanelHeading } from "@/components/Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { alertsOptions } from "@/lib/api/queries";
import type { Alert } from "@/lib/api/types";
import { COPY, cameraName, riskLabel, riskTone, timeOfDay } from "@/lib/copy";
import { cn } from "@/lib/utils";

const DOT = { hi: "bg-risk-high", mid: "bg-risk-mid", lo: "bg-risk-low" } as const;

export function AlertRow({ alert, last }: { alert: Alert; last?: boolean }) {
  const tone = riskTone(alert.risk) as keyof typeof DOT;
  return (
    <div className={cn("grid grid-cols-[auto_1fr_auto] items-start gap-3 py-3 text-body-sm", !last && "border-b border-hairline")}>
      <span aria-hidden className={cn("mt-[5px] size-2 rounded-full", DOT[tone])} />
      <div>
        <b className="font-semibold">
          {riskLabel(alert.risk)} · {cameraName(alert.camera_id)}
        </b>
        <br />
        <span className="text-ink-muted">{alert.what_next}</span>
      </div>
      <span className="text-data text-ink-muted">{timeOfDay(alert.sent_at)}</span>
    </div>
  );
}

export function AlertsPanel() {
  const { data, isPending, isError } = useQuery(alertsOptions());
  if (isError) return null;
  return (
    <Panel aria-labelledby="alerts-h">
      <PanelHeading id="alerts-h">{COPY.alertsSent}</PanelHeading>
      {isPending ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/5" />
        </div>
      ) : data.length === 0 ? (
        <p className="text-body-sm text-ink-muted">{COPY.alertsNone}</p>
      ) : (
        data.slice(0, 5).map((a, n, arr) => <AlertRow key={a.id} alert={a} last={n === arr.length - 1} />)
      )}
    </Panel>
  );
}
