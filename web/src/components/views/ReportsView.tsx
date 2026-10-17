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
import { MODES, type Mode } from "@/lib/api/types";
import { MODE_INFO, REPORT_COPY, REPORT_FILTERS, type ReportFilter, matchesFilter, plural, scoreSummary } from "@/lib/copy";
import { useSignedOff } from "@/lib/signoff";
import { cn } from "@/lib/utils";

export function ReportsView() {
  const incidents = useQuery(allIncidentsOptions());
  const pairings = useQuery(pairingsOptions());
  const metrics = useQuery(metricsOptions());
  const signed = useSignedOff();
  const [filter, setFilter] = useState<ReportFilter>("all");
  const [source, setSource] = useState<Mode | "all">("all");

  const pairFor = new Map((pairings.data ?? []).map((p) => [p.incident_id, p]));
  const all = incidents.data ?? [];
  // To review first, then riskiest first.
  const list = all
    .filter((i) => matchesFilter(i.came_true, filter) && (source === "all" || i.mode === source))
    .sort((a, b) => Number(signed.has(a.id)) - Number(signed.has(b.id)) || b.risk - a.risk);
  const toReview = all.filter((i) => !i.fixture && !signed.has(i.id)).length;
  const score = scoreSummary(metrics.data);

  return (
    <Atmosphere variant="soft">
      <AppHeader />
      <main className="mx-auto flex w-full max-w-[960px] flex-col gap-8 px-4 pt-6 pb-12 md:px-8 md:pt-10">
        <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            <h1 className="font-serif text-[40px] leading-none md:text-[52px]">{REPORT_COPY.title}</h1>
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
          <label className="flex items-center gap-2 text-[13px] text-ink-muted">
            <span className="sr-only">{REPORT_COPY.cameraSource}</span>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as Mode | "all")}
              className="h-8 cursor-pointer rounded-full border border-hairline bg-surface px-3 text-[13px] font-medium text-ink outline-none transition-colors duration-150 hover:border-ink-muted focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <option value="all">{REPORT_COPY.allCameras}</option>
              {MODES.map((m) => (
                <option key={m} value={m}>
                  {MODE_INFO[m].name} · {MODE_INFO[m].place}
                </option>
              ))}
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
