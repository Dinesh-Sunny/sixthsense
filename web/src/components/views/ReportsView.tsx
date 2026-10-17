"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { Atmosphere } from "@/components/Atmosphere";
import { ReportRow, ReportRowSkeleton } from "@/components/ReportRow";
import { SiteFooter } from "@/components/SiteFooter";
import { LostPanel } from "@/components/StatePanels";
import { Button } from "@/components/ui/button";
import { allIncidentsOptions, metricsOptions, pairingsOptions } from "@/lib/api/queries";
import type { Incident } from "@/lib/api/types";
import { REPORT_COPY, REPORT_FILTERS, type ReportFilter, matchesFilter, plural, scoreSummary } from "@/lib/copy";
import { type CameraView, VIEW_LABEL, useDataModes, viewOf } from "@/lib/incident";
import { useSignedOff } from "@/lib/signoff";
import { cn } from "@/lib/utils";

export function ReportsView() {
  const incidents = useQuery(allIncidentsOptions());
  const pairings = useQuery(pairingsOptions());
  const metrics = useQuery(metricsOptions());
  const signed = useSignedOff();
  const [filter, setFilter] = useState<ReportFilter>("all");
  // Default to the bus safety run (city until the bus run exists); the select overrides it.
  // Only the bus camera views (fallback: bus run, then city run); the select narrows to one view.
  const dataModes = useDataModes();
  const [view, setView] = useState<CameraView | "all">("all");
  const inScope = (i: Incident) => (!dataModes || dataModes.includes(i.mode)) && (view === "all" || viewOf(i) === view);

  const pairFor = new Map((pairings.data ?? []).map((p) => [p.incident_id, p]));
  const all = incidents.data ?? [];
  // To review first, then riskiest first.
  const list = all
    .filter((i) => matchesFilter(i.came_true, filter) && inScope(i))
    .sort((a, b) => Number(signed.has(a.id)) - Number(signed.has(b.id)) || b.risk - a.risk);
  const toReview = all.filter((i) => !i.fixture && !signed.has(i.id) && inScope(i)).length;
  const score = scoreSummary(metrics.data);

  return (
    <Atmosphere variant="soft">
      <AppHeader />
      <main className="mx-auto flex w-full max-w-[960px] flex-col gap-8 px-4 pt-6 pb-12 md:px-8 md:pt-10">
        <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
          <div className="flex w-full min-w-0 flex-col gap-2 sm:w-auto sm:flex-1">
            <h1 className="font-serif text-[36px] leading-none md:text-[52px]">{REPORT_COPY.title}</h1>
            <p className="min-h-5 text-body-sm text-ink-muted">
              {incidents.isSuccess ? `${plural(toReview, "report")} to review` : null}
              {score && <span> · {score}</span>}
            </p>
          </div>
          <Button asChild>
            <Link href="/run">{REPORT_COPY.checkFootage}</Link>
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div role="group" aria-label="Filter by outcome" className="flex flex-wrap gap-1">
            {REPORT_FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                aria-pressed={filter === f.id}
                onClick={() => setFilter(f.id)}
                className={cn(
                  "inline-flex h-8 items-center rounded-full border px-3.5 text-[13px] font-medium outline-none transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-ring/50",
                  filter === f.id
                    ? "border-pill bg-pill text-on-ink"
                    : "border-hairline bg-surface text-ink-muted hover:border-ink-muted hover:text-ink",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          <label className="flex w-full min-w-0 items-center gap-2 text-[13px] text-ink-muted sm:w-auto">
            <span className="sr-only">Camera view</span>
            <select
              value={view}
              onChange={(e) => setView(e.target.value as CameraView | "all")}
              className="h-8 w-full min-w-0 cursor-pointer rounded-full border border-hairline bg-surface px-3 text-[13px] font-medium text-ink outline-none transition-colors duration-150 hover:border-ink-muted focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option value="all">All views</option>
              <option value="front">{VIEW_LABEL.front}</option>
              <option value="nearside">{VIEW_LABEL.nearside}</option>
            </select>
          </label>
        </div>

        {incidents.isError ? (
          <LostPanel onRetry={() => void incidents.refetch()} />
        ) : incidents.isPending ? (
          <ul className="flex flex-col gap-3">
            <ReportRowSkeleton />
            <ReportRowSkeleton />
            <ReportRowSkeleton />
          </ul>
        ) : list.length === 0 ? (
          <div className="flex flex-col gap-2 rounded-lg border border-hairline bg-surface p-7">
            <h2 className="font-serif text-[28px] leading-[1.15]">
              {all.length === 0 ? REPORT_COPY.emptyTitle : REPORT_COPY.noneTitle}
            </h2>
            <p className="text-body-sm text-ink-muted">{all.length === 0 ? REPORT_COPY.emptyBody : REPORT_COPY.noneBody}</p>
          </div>
        ) : (
          <ul className="flex flex-col gap-3">
            {list.map((i) => (
              <ReportRow key={i.id} incident={i} pairing={pairFor.get(i.id)} signedOff={signed.has(i.id)} />
            ))}
          </ul>
        )}
        <p className="text-data text-ink-muted">{REPORT_COPY.standIn}</p>
      </main>
      <SiteFooter />
    </Atmosphere>
  );
}
