"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { Atmosphere } from "@/components/Atmosphere";
import { ClipPlayer } from "@/components/ClipPlayer";
import { GapChart } from "@/components/GapChart";
import { HowItDecided } from "@/components/HowItDecided";
import { Panel, PanelHeading } from "@/components/Panel";
import { SiteFooter } from "@/components/SiteFooter";
import { LostPanel } from "@/components/StatePanels";
import { StatusPill } from "@/components/StatusPill";
import { Wordmark } from "@/components/Wordmark";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { alertsOptions, incidentOptions, queryKeys, sendAlert } from "@/lib/api/queries";
import type { Incident } from "@/lib/api/types";
import { COPY, SAMPLE, VERDICT, cameraLine, cameraName, riskLabel, riskTone, timeOfDay } from "@/lib/copy";
import { cn } from "@/lib/utils";

function Timeline({ incident: i }: { incident: Incident }) {
  const checked = i.came_true !== "unknown";
  const verdictBorder = { yes: "border-truth text-truth", partly: "border-risk-mid text-risk-mid", no: "border-risk-high text-risk-high", unknown: "border-slate text-slate" }[i.came_true];
  return (
    <Panel aria-labelledby="tl-h">
      <PanelHeading id="tl-h">{COPY.timeline}</PanelHeading>
      <div className="grid grid-cols-6 gap-1.5">
        <div className="h-11 rounded-[6px] bg-surface-sunk" />
        <div className="h-11 rounded-[6px] bg-surface-sunk" />
        <div className="col-span-2 grid h-11 place-items-center rounded-[6px] bg-ink px-1 text-center font-mono text-[11px] font-medium text-on-ink sm:col-span-1">
          {COPY.predictedHere}
        </div>
        <div className={cn("col-span-2 grid h-11 place-items-center rounded-[6px] border-2 px-1 text-center font-mono text-[11px] font-medium sm:col-span-1", verdictBorder)}>
          {checked ? COPY.checkedHere : COPY.waiting}
        </div>
        <div className="hidden h-11 rounded-[6px] bg-surface-sunk sm:block" />
        <div className="hidden h-11 rounded-[6px] bg-surface-sunk sm:block" />
      </div>
    </Panel>
  );
}

function NextStep({ incident: i }: { incident: Incident }) {
  const queryClient = useQueryClient();
  const alerts = useQuery(alertsOptions());
  const existing = alerts.data?.find((a) => a.incident_id === i.id);
  const [copied, setCopied] = useState(false);
  const [showHow, setShowHow] = useState(false);
  const alert = useMutation({
    mutationFn: () => sendAlert(i.id),
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.alerts }),
  });
  const sentAt = alert.data?.sent_at ?? existing?.sent_at;
  const sent = alert.isPending || alert.isSuccess || Boolean(existing);

  return (
    <Panel className="flex flex-col gap-3" aria-labelledby="next-h">
      <PanelHeading id="next-h" className="mb-0">
        {COPY.nextStep}
      </PanelHeading>
      <div className="flex flex-wrap gap-3">
        {!i.fixture && (
          <Button onClick={() => alert.mutate()} disabled={sent}>
            {sent ? (sentAt ? `Sent at ${timeOfDay(sentAt)}` : "Sending…") : COPY.sendAlert}
          </Button>
        )}
        <Button
          variant="glass"
          onClick={() => {
            void navigator.clipboard?.writeText(window.location.href).then(() => setCopied(true));
          }}
        >
          {copied ? COPY.linkCopied : COPY.copyLink}
        </Button>
      </div>
      {sentAt && (
        <div>
          <StatusPill tone="ok">Alert sent at {timeOfDay(sentAt)}</StatusPill>
        </div>
      )}
      {alert.data && !alert.data.delivered && <p className="text-body-sm text-ink-muted">{COPY.alertNotDelivered}</p>}
      {alert.isError && <p className="text-body-sm text-risk-high">We couldn&apos;t send the alert. Try again in a moment.</p>}
      <button
        type="button"
        className="self-start text-data text-slate underline-offset-2 hover:underline"
        aria-expanded={showHow}
        onClick={() => setShowHow((v) => !v)}
      >
        {COPY.seeHow} {showHow ? "↑" : "→"}
      </button>
      {showHow && <HowItDecided incident={i} />}
    </Panel>
  );
}

function Forecast({ incident: i }: { incident: Incident }) {
  const verdict = VERDICT[i.came_true];
  const verdictBorder = { yes: "border-truth", partly: "border-risk-mid", no: "border-risk-high", unknown: "" }[i.came_true];
  return (
    <>
        <Panel className="flex flex-col gap-2.5">
          <div className="text-eye">{COPY.prediction}</div>
          <h1 className="font-serif text-[28px] leading-[1.12] text-balance md:text-[34px]">{i.what_next}</h1>
          {i.what_happens && (
            <p className="text-body-sm text-ink-muted">
              <b className="font-medium text-ink">{COPY.now}</b> {i.what_happens}
            </p>
          )}
          {i.why && (
            <p className="text-body-sm text-ink-muted">
              <b className="font-medium text-ink">{COPY.why}</b> {i.why}
            </p>
          )}
          {i.fix && (
            <p className="text-body-sm text-ink-muted">
              <b className="font-medium text-ink">{COPY.fix}</b> {i.fix}
            </p>
          )}
          {i.fixture && <p className="text-body-sm text-ink-muted">{COPY.sampleBody}</p>}
        </Panel>
        <Panel className={cn("flex flex-col gap-2.5", verdictBorder)}>
          <div className="flex items-center gap-3">
            <div className="text-eye">{COPY.whatHappened}</div>
            <div className="flex-1" />
            <StatusPill tone={i.fixture ? "sample" : verdict.tone}>{i.fixture ? SAMPLE.label : verdict.label}</StatusPill>
          </div>
          {i.came_true === "unknown" ? (
            <p className="text-body-sm text-ink-muted">{COPY.notCheckedYet}</p>
          ) : (
            <>
              <p className="text-body-sm text-ink">{i.came_true_evidence}</p>
              <div className="text-data text-ink-muted">{COPY.checkedByWatching}</div>
            </>
          )}
        </Panel>
    </>
  );
}

function DetailBody({ incident: i }: { incident: Incident }) {
  return (
    <div className="grid grid-cols-1 gap-6 px-4 pb-8 md:px-8 lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
      <section className="flex flex-col gap-4">
        <div className="overflow-hidden rounded-lg bg-surface shadow-float">
          <ClipPlayer
            source={i.source}
            controls
            large
            label={`Clip from ${cameraName(i.camera_id)}`}
            fallbackLabel={COPY.noClip}
            overlay={
              i.fixture ? (
                <StatusPill tone="sample">{SAMPLE.label}</StatusPill>
              ) : (
                <StatusPill tone={riskTone(i.risk)}>{riskLabel(i.risk)}</StatusPill>
              )
            }
          />
        </div>
        <div className="flex flex-col gap-4 lg:hidden">
          <Forecast incident={i} />
        </div>
        <Timeline incident={i} />
        {i.gap_series.length > 1 && (
          <Panel aria-labelledby="gap-h">
            <PanelHeading id="gap-h">{COPY.whyTrust}</PanelHeading>
            <GapChart series={i.gap_series} />
          </Panel>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <div className="hidden flex-col gap-4 lg:flex">
          <Forecast incident={i} />
        </div>
        <NextStep incident={i} />
      </section>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 px-4 pb-8 md:px-8 lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]" aria-busy>
      <Skeleton className="aspect-video rounded-lg" />
      <div className="flex flex-col gap-4">
        <Skeleton className="h-40 rounded-panel" />
        <Skeleton className="h-24 rounded-panel" />
      </div>
    </div>
  );
}

export function DetailView() {
  const id = useSearchParams().get("id") ?? "";
  const q = useQuery(incidentOptions(id));
  const i = q.data;
  const notFound = !id || (q.error instanceof ApiError && q.error.status === 404);

  return (
    <Atmosphere variant="soft">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-5 md:px-8">
        <Button asChild variant="glass" size="sm">
          <Link href={i ? { pathname: "/dashboard", query: { mode: i.mode } } : "/dashboard"}>← {COPY.allMoments}</Link>
        </Button>
        <Link href="/" aria-label="SixthSense home">
          <Wordmark />
        </Link>
        <div className="flex-1" />
        {i && <span className="text-data text-ink-muted">{cameraLine(i)}</span>}
      </header>
      {notFound ? (
        <div className="px-4 md:px-8">
          <LostPanel title={COPY.notFound} body={COPY.notFoundBody} onRetry={() => void q.refetch()} />
        </div>
      ) : q.isError ? (
        <div className="px-4 md:px-8">
          <LostPanel onRetry={() => void q.refetch()} />
        </div>
      ) : !i ? (
        <DetailSkeleton />
      ) : (
        <DetailBody incident={i} />
      )}
      <SiteFooter />
    </Atmosphere>
  );
}

