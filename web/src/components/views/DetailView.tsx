"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { Atmosphere } from "@/components/Atmosphere";
import { ClipPlayer } from "@/components/ClipPlayer";
import { GapChart } from "@/components/GapChart";
import { HowItDecided } from "@/components/HowItDecided";
import { Panel, PanelHeading } from "@/components/Panel";
import { SiteFooter } from "@/components/SiteFooter";
import { LostPanel } from "@/components/StatePanels";
import { StatusPill } from "@/components/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { alertsOptions, incidentOptions, pairingsOptions, queryKeys, sendAlert } from "@/lib/api/queries";
import type { Alert, Incident, Pairing } from "@/lib/api/types";
import {
  BUS_COPY,
  COPY,
  REPORT_COPY,
  SAMPLE,
  TIMELINE_STEP,
  VERDICT,
  cameraLine,
  cameraName,
  gapLine,
  gapSummary,
  reportId,
  riskLabel,
  riskTone,
  routeLine,
  timeOfDay,
} from "@/lib/copy";
import { useSignOff } from "@/lib/signoff";
import { incidentTitle } from "@/lib/incident";
import { cn } from "@/lib/utils";

function Breadcrumb({ id }: { id: string }) {
  return (
    <nav aria-label="Breadcrumb" className="text-body-sm text-ink-muted">
      <ol className="flex items-center gap-2">
        <li>
          <Link href="/reports" className="rounded-sm underline-offset-2 outline-none hover:text-ink hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50">
            Reports
          </Link>
        </li>
        <li aria-hidden>/</li>
        <li aria-current="page" className="font-mono text-ink">
          {id ? reportId(id) : "Report"}
        </li>
      </ol>
    </nav>
  );
}

function Section({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-1.5 border-t border-hairline pt-4 first:border-t-0 first:pt-0", className)}>
      <div className="text-eye">{label}</div>
      {children}
    </div>
  );
}

function Report({ incident: i, pairing, signedOff }: { incident: Incident; pairing?: Pairing; signedOff: boolean }) {
  const verdict = VERDICT[i.came_true];
  return (
    <Panel className="flex flex-col gap-4 p-6">
      <h1 className="font-serif text-[26px] leading-[1.15] text-balance md:text-[30px]">{incidentTitle(i, pairing)}</h1>
      {i.what_happens && (
        <Section label={REPORT_COPY.before}>
          <p className="text-body-sm text-ink">{i.what_happens}</p>
        </Section>
      )}
      <Section label={REPORT_COPY.forecast}>
        <p className="font-serif text-xl leading-[1.25] text-balance">{i.what_next}</p>
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
      </Section>
      <Section label={REPORT_COPY.whatHappened}>
        {i.fixture ? (
          <p className="text-body-sm text-ink-muted">{COPY.sampleBody}</p>
        ) : i.came_true === "unknown" ? (
          <p className="text-body-sm text-ink-muted">{COPY.notCheckedYet}</p>
        ) : (
          <>
            <p className="text-body-sm text-ink">{i.came_true_evidence}</p>
            <p className="text-data text-ink-muted">{COPY.checkedByWatching}</p>
          </>
        )}
      </Section>
      <Section label={REPORT_COPY.outcome}>
        <div className="flex flex-wrap items-center gap-2">
          {i.fixture ? (
            <StatusPill tone="sample">{SAMPLE.label}</StatusPill>
          ) : (
            <StatusPill tone={verdict.tone}>{verdict.label}</StatusPill>
          )}
          <span className="text-data text-ink-muted">{signedOff ? REPORT_COPY.signedOffByYou : REPORT_COPY.toReview}</span>
        </div>
      </Section>
    </Panel>
  );
}

type Step = { label: string; detail?: string; done: boolean };

function agentSteps(i: Incident, alert: Alert | undefined): Step[] {
  const gap = gapSummary(i.gap_series);
  const steps: Step[] = [{ label: TIMELINE_STEP.spotted, detail: cameraLine(i), done: true }];
  if (i.verified) steps.push({ label: TIMELINE_STEP.boxes, detail: gap ? gapLine(gap) : undefined, done: true });
  steps.push({ label: TIMELINE_STEP.forecast, detail: riskLabel(i.risk), done: true });
  if (alert) steps.push({ label: TIMELINE_STEP.nudged, detail: `At ${timeOfDay(alert.sent_at)}`, done: true });
  const checked = i.came_true !== "unknown";
  steps.push({
    label: TIMELINE_STEP.checked,
    detail: checked ? VERDICT[i.came_true].label : REPORT_COPY.waitingClip,
    done: checked,
  });
  if (i.came_true === "yes") steps.push({ label: TIMELINE_STEP.filed, detail: reportId(i.id), done: true });
  return steps;
}

function Timeline({ incident, alert }: { incident: Incident; alert: Alert | undefined }) {
  const steps = agentSteps(incident, alert);
  return (
    <Panel aria-labelledby="tl-h" className="p-6">
      <PanelHeading id="tl-h">{REPORT_COPY.timeline}</PanelHeading>
      <ol className="flex flex-col">
        {steps.map((s, n) => (
          <li key={s.label} className="relative flex gap-3 pb-4 last:pb-0">
            {n < steps.length - 1 && <span aria-hidden className="absolute top-3 left-[4.5px] h-full w-px bg-hairline" />}
            <span
              aria-hidden
              className={cn(
                "relative mt-1.5 size-2.5 shrink-0 rounded-full",
                s.done ? "bg-ink" : "border border-ink-muted bg-surface",
              )}
            />
            <div className="flex min-w-0 flex-col">
              <span className={cn("text-body-sm font-medium", s.done ? "text-ink" : "text-ink-muted")}>
                {s.label}
                <span className="sr-only">{s.done ? " (done)" : " (waiting)"}</span>
              </span>
              {s.detail && <span className="text-data text-ink-muted">{s.detail}</span>}
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  );
}

function Actions({ incident: i, pairing, alert }: { incident: Incident; pairing: Pairing | undefined; alert: Alert | undefined }) {
  const queryClient = useQueryClient();
  const { signedOff, setSignedOff } = useSignOff(i.id);
  const [showHow, setShowHow] = useState(false);
  const send = useMutation({
    mutationFn: () => sendAlert(i.id),
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.alerts }),
  });
  const sentAt = send.data?.sent_at ?? alert?.sent_at;
  // Idempotent: one alert per report, whoever sent it (map nudge or this page).
  const sent = send.isPending || Boolean(sentAt);

  return (
    <Panel aria-labelledby="act-h" className="flex flex-col gap-4 p-6">
      <PanelHeading id="act-h" className="mb-0">
        {REPORT_COPY.actions}
      </PanelHeading>
      {!i.fixture && (
        <div className="flex flex-wrap items-center gap-3">
          {signedOff ? (
            <>
              <StatusPill tone="ok">{REPORT_COPY.signedOffByYou}</StatusPill>
              <Button variant="link" size="sm" onClick={() => setSignedOff(false)}>
                {REPORT_COPY.undo}
              </Button>
            </>
          ) : (
            <Button onClick={() => setSignedOff(true)}>{REPORT_COPY.signOff}</Button>
          )}
          <Button variant="outline" onClick={() => send.mutate()} disabled={sent}>
            {send.isPending ? REPORT_COPY.sending : sentAt ? `Sent at ${timeOfDay(sentAt)}` : REPORT_COPY.sendGarage}
          </Button>
        </div>
      )}
      {send.data && send.data.delivered === false && <p className="text-body-sm text-ink-muted">{REPORT_COPY.notDelivered}</p>}
      {send.isError && <p className="text-body-sm text-risk-high">{REPORT_COPY.sendFailed}</p>}
      {pairing && (
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="outline" size="sm">
            <Link href={{ pathname: "/dashboard", query: { bus: pairing.vehicle_id, route: pairing.route } }}>
              {REPORT_COPY.showOnMap}
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href={{ pathname: "/coaching", query: { route: pairing.route } }}>{REPORT_COPY.coachingRoute}</Link>
          </Button>
        </div>
      )}
      <button
        type="button"
        className="self-start rounded-sm text-data text-slate underline-offset-2 outline-none hover:text-ink hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50"
        aria-expanded={showHow}
        onClick={() => setShowHow((v) => !v)}
      >
        {COPY.seeHow} {showHow ? "↑" : "→"}
      </button>
      {showHow && <HowItDecided incident={i} />}
    </Panel>
  );
}

function DetailBody({ incident: i }: { incident: Incident }) {
  const pairings = useQuery(pairingsOptions());
  const alerts = useQuery(alertsOptions());
  const pairing = pairings.data?.find((p) => p.incident_id === i.id);
  const alert = alerts.data?.find((a) => a.incident_id === i.id);
  const { signedOff } = useSignOff(i.id);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
      <section className="flex flex-col gap-6">
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
                <span className="flex gap-2">
                  <StatusPill tone="unk" className="bg-surface">
                    {BUS_COPY.standIn}
                  </StatusPill>
                  <StatusPill tone={riskTone(i.risk)} className="bg-surface">
                    {riskLabel(i.risk)}
                  </StatusPill>
                </span>
              )
            }
          />
        </div>
        <div className="lg:hidden">
          <Report incident={i} pairing={pairing} signedOff={signedOff} />
        </div>
        {i.gap_series.length > 1 && (
          <Panel aria-labelledby="gap-h" className="p-6">
            <PanelHeading id="gap-h">{REPORT_COPY.evidence}</PanelHeading>
            <GapChart series={i.gap_series} />
          </Panel>
        )}
        <Timeline incident={i} alert={alert} />
      </section>
      <section className="flex flex-col gap-6">
        <div className="hidden lg:block">
          <Report incident={i} pairing={pairing} signedOff={signedOff} />
        </div>
        <Actions incident={i} pairing={pairing} alert={alert} />
      </section>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]" aria-busy>
      <Skeleton className="aspect-video rounded-lg" />
      <div className="flex flex-col gap-4">
        <Skeleton className="h-56 rounded-panel" />
        <Skeleton className="h-28 rounded-panel" />
      </div>
    </div>
  );
}

export function DetailView() {
  const id = useSearchParams().get("id") ?? "";
  const q = useQuery(incidentOptions(id));
  const pairings = useQuery(pairingsOptions());
  const i = q.data;
  const notFound = !id || (q.error instanceof ApiError && q.error.status === 404);
  const pairing = pairings.data?.find((p) => p.incident_id === id);

  return (
    <Atmosphere variant="soft">
      <AppHeader />
      <main className="mx-auto flex w-full max-w-[1200px] flex-col gap-6 px-4 pt-4 pb-12 md:px-8 md:pt-8">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
          <Breadcrumb id={id} />
          {i && !i.fixture && <span className="text-data text-ink-muted">{routeLine(pairing)}</span>}
        </div>
        {notFound ? (
          <LostPanel title={COPY.notFound} body={COPY.notFoundBody} onRetry={() => void q.refetch()} />
        ) : q.isError ? (
          <LostPanel onRetry={() => void q.refetch()} />
        ) : !i ? (
          <DetailSkeleton />
        ) : (
          <DetailBody incident={i} />
        )}
        <p className="text-data text-ink-muted">{REPORT_COPY.standIn}</p>
      </main>
      <SiteFooter />
    </Atmosphere>
  );
}
