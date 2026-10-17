"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ClipPlayer } from "@/components/ClipPlayer";
import { StatusPill } from "@/components/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { incidentOptions } from "@/lib/api/queries";
import type { Incident } from "@/lib/api/types";
import { BUS_COPY, COPY, SAMPLE, VERDICT, cameraLine, cameraName, gapLine, gapSummary, riskLabel, riskTone } from "@/lib/copy";

export function incidentHref(id: string) {
  return { pathname: "/incident" as const, query: { id } };
}

export function IncidentCard({ incident: i, busId }: { incident: Incident; busId?: string }) {
  const queryClient = useQueryClient();
  const prefetch = () => {
    void queryClient.query(incidentOptions(i.id)).catch(() => {});
  };
  const gap = gapSummary(i.gap_series);
  const verdict = VERDICT[i.came_true];

  return (
    <article
      className="flex flex-col overflow-hidden rounded-xl bg-surface shadow-float"
      onMouseEnter={prefetch}
      onFocus={prefetch}
    >
      <ClipPlayer
        source={i.source}
        label={`Clip from ${cameraName(i.camera_id)}`}
        fallbackLabel={cameraLine(i)}
        overlay={
          i.fixture ? (
            <StatusPill tone="sample">{SAMPLE.label}</StatusPill>
          ) : (
            <StatusPill tone={riskTone(i.risk)}>{riskLabel(i.risk)}</StatusPill>
          )
        }
      />
      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="text-data text-ink-muted">{cameraLine(i)}</div>
        <div className="text-eye">{COPY.next}</div>
        <p className="text-forecast">{i.what_next}</p>
        {i.fixture ? (
          <p className="text-body-sm text-ink-muted">{COPY.sampleBody}</p>
        ) : (
          i.why && (
            <p className="text-body-sm text-ink-muted">
              <b className="font-medium text-ink">{COPY.why}</b> {i.why}
            </p>
          )
        )}
        {gap && <div className="text-data text-ink-muted">{gapLine(gap)}</div>}
      </div>
      <div className="flex items-center gap-2 border-t border-hairline px-4 py-3">
        {i.fixture ? (
          <StatusPill tone="unk">{SAMPLE.example}</StatusPill>
        ) : (
          <StatusPill tone={verdict.tone}>{verdict.label}</StatusPill>
        )}
        {busId && (
          <Button asChild size="sm" variant="glass" className="ml-auto">
            <Link href={{ pathname: "/dashboard", query: { bus: busId } }}>{BUS_COPY.showOnMap}</Link>
          </Button>
        )}
        <Button asChild size="sm" className={busId ? undefined : "ml-auto"}>
          <Link href={incidentHref(i.id)} onMouseEnter={prefetch} onFocus={prefetch}>
            {COPY.view}
          </Link>
        </Button>
      </div>
    </article>
  );
}

export function IncidentCardSkeleton() {
  return (
    <article className="flex flex-col overflow-hidden rounded-xl bg-surface shadow-float" aria-hidden>
      <Skeleton className="aspect-video rounded-none" />
      <div className="flex flex-col gap-2 p-4">
        <Skeleton className="h-3 w-2/5" />
        <Skeleton className="h-[22px] w-[90%]" />
        <Skeleton className="h-[22px] w-[70%]" />
        <Skeleton className="h-3 w-3/5" />
      </div>
    </article>
  );
}
