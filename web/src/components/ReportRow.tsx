"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { StatusPill } from "@/components/StatusPill";
import { Skeleton } from "@/components/ui/skeleton";
import { ClipStill } from "@/components/ClipStill";
import { incidentOptions } from "@/lib/api/queries";
import type { Incident, Pairing } from "@/lib/api/types";
import { VIEW_LABEL, incidentTitle, shortLine, viewOf } from "@/lib/incident";
import { REPORT_COPY, SAMPLE, VERDICT, reportId, routeLine } from "@/lib/copy";

/** First frame of the clip, muted and inert: the row's overlay link takes every click. */
function Thumb({ source, view }: { source: string | null; view: string | null }) {
  return (
    <div aria-hidden className="relative aspect-video w-24 shrink-0 overflow-hidden rounded-md bg-surface-sunk sm:w-36">
      {source && <ClipStill source={source} alt="" />}
      {view && (
        <span className="absolute bottom-1 left-1 rounded-full bg-scrim px-1.5 py-0.5 text-[10px] leading-none font-medium text-on-sky">
          {view}
        </span>
      )}
    </div>
  );
}

/** One report in a list. The whole row is a single link to the report. */
export function ReportRow({
  incident: i,
  pairing,
  signedOff,
  secondary = "fix",
}: {
  incident: Incident;
  pairing?: Pairing;
  signedOff: boolean;
  /** Which short line to show; coaching shows the fix as its habit, so its rows show what happened. */
  secondary?: "fix" | "happened";
}) {
  const queryClient = useQueryClient();
  const prefetch = () => {
    queryClient.setQueryData(incidentOptions(i.id).queryKey, i);
  };
  const verdict = VERDICT[i.came_true];
  return (
    <li className="group relative flex items-center gap-4 rounded-lg border border-hairline bg-surface p-3 transition-colors duration-150 hover:border-ink-muted has-[a:focus-visible]:ring-[3px] has-[a:focus-visible]:ring-ring/50 sm:gap-5 sm:p-4">
      <Thumb source={i.source} view={viewOf(i) ? VIEW_LABEL[viewOf(i)!] : null} />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-data text-ink-muted">
          <span className="font-medium text-ink">{reportId(i.id)}</span>
          <span>{routeLine(pairing)}</span>
        </div>
        <Link
          href={{ pathname: "/incident", query: { id: i.id } }}
          onMouseEnter={prefetch}
          onFocus={prefetch}
          className="line-clamp-2 text-body-sm font-medium text-ink outline-none after:absolute after:inset-0 after:rounded-lg after:content-[''] group-hover:underline group-hover:underline-offset-2"
        >
          {incidentTitle(i, pairing)}
        </Link>
        {shortLine(i, secondary) && <p className="line-clamp-1 text-body-sm text-ink-muted">{shortLine(i, secondary)}</p>}
        <div className="flex flex-wrap items-center gap-2">
          {i.fixture ? (
            <StatusPill tone="sample">{SAMPLE.label}</StatusPill>
          ) : (
            <StatusPill tone={verdict.tone}>{verdict.label}</StatusPill>
          )}
          <span className={signedOff ? "text-data text-ink-muted" : "text-data font-medium text-ink"}>
            {signedOff ? REPORT_COPY.signedOff : REPORT_COPY.toReview}
          </span>
        </div>
      </div>
      <span aria-hidden className="hidden text-ink-muted transition-transform duration-150 group-hover:translate-x-0.5 sm:block">
        →
      </span>
    </li>
  );
}

export function ReportRowSkeleton() {
  return (
    <li aria-hidden className="flex items-center gap-4 rounded-lg border border-hairline bg-surface p-3 sm:gap-5 sm:p-4">
      <Skeleton className="aspect-video w-24 rounded-md sm:w-36" />
      <div className="flex flex-1 flex-col gap-2">
        <Skeleton className="h-3 w-2/5" />
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-5 w-24 rounded-full" />
      </div>
    </li>
  );
}
