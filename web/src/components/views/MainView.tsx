"use client";

import { useQuery } from "@tanstack/react-query";
import type { Route } from "next";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import { AccuracyMeter } from "@/components/AccuracyMeter";
import { AlertsPanel } from "@/components/AlertsPanel";
import { AskBox } from "@/components/AskBox";
import { Atmosphere } from "@/components/Atmosphere";
import { IncidentCard, IncidentCardSkeleton } from "@/components/IncidentCard";
import { ModeTabs } from "@/components/ModeTabs";
import { Panel, PanelHeading } from "@/components/Panel";
import { SiteFooter } from "@/components/SiteFooter";
import { CalmPanel, LostPanel } from "@/components/StatePanels";
import { WeatherPill } from "@/components/WeatherPill";
import { Wordmark } from "@/components/Wordmark";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { incidentsOptions, metricsOptions } from "@/lib/api/queries";
import { MODES, type Mode, type ModeMetrics } from "@/lib/api/types";
import { COPY, MODE_INFO, calmBody, heroSubline, momentsHeadline } from "@/lib/copy";

const FALLBACK_MODE: Mode = "road";

function parseMode(v: string | null): Mode | null {
  return MODES.includes(v as Mode) ? (v as Mode) : null;
}

/** No ?mode: open the camera with the most moments from its latest run. */
function busiestMode(metrics: ModeMetrics[] | undefined): Mode {
  const best = metrics?.filter((m) => m.verified > 0).sort((a, b) => b.verified - a.verified)[0];
  return best?.mode ?? FALLBACK_MODE;
}

export function MainView() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [, startTransition] = useTransition();
  const metrics = useQuery(metricsOptions());
  const asked = parseMode(params.get("mode"));
  // Wait for metrics before picking a default so the page doesn't jump between tabs.
  const modeKnown = asked !== null || !metrics.isPending;
  const mode = asked ?? busiestMode(metrics.data);

  const incidents = useQuery({ ...incidentsOptions(mode), enabled: modeKnown });
  const m = metrics.data?.find((x) => x.mode === mode);
  const list = incidents.data ?? [];

  const setMode = (next: Mode) =>
    startTransition(() => {
      router.replace(`${pathname}?mode=${next}` as Route, { scroll: false });
    });

  return (
    <Atmosphere variant="band">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-5 md:px-8">
        <Wordmark onSky />
        <WeatherPill />
        <div className="hidden flex-1 md:block" />
        <ModeTabs mode={mode} metrics={metrics.data} onChange={setMode} />
        <div className="flex-1" />
        <Link href="/about" className="text-[13px] font-medium text-on-sky-muted underline-offset-4 hover:underline">
          About
        </Link>
        <Button asChild variant="glass" size="sm">
          <Link href="/run">{COPY.watchCamera}</Link>
        </Button>
      </header>

      <section className="flex flex-wrap items-end gap-6 px-4 pt-7 pb-9 md:px-8">
        <div className="flex min-w-0 flex-col gap-2">
          {incidents.isPending ? (
            <Skeleton className="h-14 w-[min(520px,80vw)] bg-glass" />
          ) : (
            <h1 className="font-serif text-[40px] leading-none text-on-sky md:text-[56px]">
              {momentsHeadline(incidents.isError ? 0 : list.length)}
            </h1>
          )}
          <p className="text-base text-on-sky-muted">{heroSubline(mode, m, list.length > 0 && list.every((i) => i.fixture))}</p>
        </div>
        <div className="hidden flex-1 md:block" />
        {m && (
          <div className="glass rounded-panel px-[18px] py-3.5 shadow-float">
            <AccuracyMeter metrics={m} />
          </div>
        )}
      </section>

      <div className="flex flex-col gap-6 px-4 pb-8 md:px-8 lg:flex-row">
        <main className="flex min-w-0 flex-1 flex-col gap-4">
          <div className="text-eye">{COPY.riskiestFirst}</div>
          {incidents.isError ? (
            <LostPanel onRetry={() => void incidents.refetch()} />
          ) : incidents.isPending ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <IncidentCardSkeleton />
              <IncidentCardSkeleton />
            </div>
          ) : list.length === 0 ? (
            <CalmPanel title={MODE_INFO[mode].calm} body={calmBody(m)} />
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {list.map((i) => (
                <IncidentCard key={i.id} incident={i} />
              ))}
            </div>
          )}
        </main>

        <aside className="flex w-full flex-col gap-4 lg:w-80">
          <Panel aria-labelledby="ask-h">
            <PanelHeading id="ask-h">{COPY.ask}</PanelHeading>
            <AskBox showChips={false} />
          </Panel>
          <AlertsPanel />
          <Panel aria-labelledby="how-h">
            <PanelHeading id="how-h">{COPY.howItWorks}</PanelHeading>
            <p className="text-body-sm text-ink-muted">{COPY.howItWorksBody}</p>
          </Panel>
        </aside>
      </div>
      <SiteFooter />
    </Atmosphere>
  );
}
