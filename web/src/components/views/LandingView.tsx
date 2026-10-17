"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { BuiltWith } from "@/components/landing/BuiltWith";
import { CheckTimeline } from "@/components/landing/CheckTimeline";
import { MapTile, ReportStack } from "@/components/landing/AudienceCreatives";
import { CoachFan } from "@/components/landing/CoachFan";
import { GapCreative } from "@/components/landing/GapCreative";
import { HeroStage } from "@/components/landing/HeroStage";
import { LiveLines } from "@/components/landing/LiveLines";
import { LiveResults } from "@/components/landing/LiveResults";
import { Team } from "@/components/landing/Team";
import { Reveal, rise, stagger } from "@/components/landing/reveal";
import { ScoreBar } from "@/components/landing/ScoreBar";
import { StatusPill } from "@/components/StatusPill";
import { WeatherPill } from "@/components/WeatherPill";
import { Button } from "@/components/ui/button";
import { incidentsOptions, metricsOptions, readyOptions, weatherOptions } from "@/lib/api/queries";
import type { Incident, ModeMetrics } from "@/lib/api/types";
import { BUS_COPY, COPY, MODE_INFO, STORE_LABEL, gapLine, gapSummary, riskLabel, riskTone, scoreLine } from "@/lib/copy";
import { hazardOf } from "@/lib/incident";
import { assetUrl, cn } from "@/lib/utils";

const GITHUB_URL = "https://github.com/Dinesh-Sunny/sixthsense";

// Real frames from the archive the agent watches (public/landing).
const FRAMES = {
  hero: { src: "/landing/f0.jpg", alt: "A San Francisco crossing seen from a street camera, people on the zebra crossing" },
  watch: { src: "/landing/f3.jpg", alt: "A city intersection seen from above, cars and people waiting to cross" },
  ruleOut: { src: "/landing/f3.jpg", alt: "A city intersection from above, cars and people waiting to cross" },
  predict: { src: "/landing/f1.jpg", alt: "A New York crossing with pedestrians and a cyclist" },
};


const STEPS = [
  {
    title: "It watches\nevery clip",
    body: "Every bus camera, every clip. It searches the footage for risky moments, so nothing waits for a person to press play.",
    plain: "Under the hood: semantic search over the VAST video archive.",
  },
  {
    title: "It rules out\nfalse alarms",
    body: "Before anyone is bothered, it tracks every car and person frame by frame. If two of them aren't really closing in, the moment is dropped.",
    plain: "Under the hood: YOLO11 boxes and a tracker measure the gap in car lengths.",
  },
  {
    title: "It sees what\nhappens next",
    body: "For every real moment, it predicts the next few seconds, says why, and suggests one practical fix. In plain words, with the vehicle and the time.",
    plain: "Under the hood: Cosmos3-Reason watches the clip and answers in a fixed format.",
  },
  {
    title: "Then it checks\nitself",
    body: "It watches the next clip and marks each prediction: came true, partly, or didn't happen. You get a score measured on your own footage, not a promise.",
    plain: "Under the hood: the next clip is judged against the prediction, and the score is saved.",
  },
];

const AUDIENCES = [
  { title: "Bus safety teams", body: "See which buses had a close call today, with the clip and what happened next." },
  { title: "Control rooms", body: "Every live bus on one map, sorted so the ones that need a look come first." },
  { title: "Driver coaches", body: "One card per route with the moments and fixes to talk through with drivers." },
];

function Frame({ frame, className }: { frame: { src: string; alt: string }; className?: string }) {
  return <img src={assetUrl(frame.src)} alt={frame.alt} className={cn("block size-full object-cover", className)} />;
}

function WordmarkLarge({ className }: { className?: string }) {
  return (
    <span className={cn("font-serif leading-[0.95] text-ink", className)}>
      Sixth<i className="text-wordmark-accent">Sense</i>
    </span>
  );
}

/** Real incidents, riskiest first, one per distinct forecast sentence. */
function rankDistinct(lists: (Incident[] | undefined)[]): Incident[] {
  const seen = new Set<string>();
  return lists
    .flatMap((l) => l ?? [])
    .filter((i) => !i.fixture)
    .sort((a, b) => b.risk - a.risk)
    .filter((i) => (seen.has(i.what_next) ? false : (seen.add(i.what_next), true)));
}

function topIncident(lists: (Incident[] | undefined)[]): Incident | undefined {
  return lists
    .flatMap((l) => l ?? [])
    .filter((i) => !i.fixture)
    .sort((a, b) => b.risk - a.risk || Number(b.came_true === "yes") - Number(a.came_true === "yes"))[0];
}

function proofLine(m: ModeMetrics): string {
  return `${m.came_true_yes} of ${m.checked} predictions came true on the latest ${m.mode} run`;
}

function bestScore(metrics: ModeMetrics[] | undefined): ModeMetrics | undefined {
  return metrics?.filter((m) => m.checked > 0).sort((a, b) => b.checked - a.checked)[0];
}

function FeatureRow({
  index,
  visual,
  wash,
}: {
  index: number;
  visual: React.ReactNode;
  wash: "sky-card" | "lav-card" | "dusk-card";
}) {
  const step = STEPS[index];
  const flip = index % 2 === 1;
  return (
    <div className="grid grid-cols-1 items-center gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)] lg:gap-[72px]">
      <div className={cn("flex flex-col gap-4", flip && "lg:order-2")}>
        <span className="font-mono text-[11px] leading-none font-medium tracking-[0.06em] text-slate uppercase">
          Step {index + 1}
        </span>
        <h2 className="font-serif text-[36px] leading-[1.08] whitespace-pre-line md:text-[44px]">{step.title}</h2>
        <p className="max-w-[400px] text-[15px] leading-[23px] text-ink-muted">{step.body}</p>
        <p className="max-w-[400px] text-data text-ink-muted">{step.plain}</p>
      </div>
      <div
        className={cn(
          "grid min-h-[320px] place-items-center rounded-xl p-6 md:min-h-[400px]",
          wash,
          flip && "lg:order-1",
        )}
      >
        {visual}
      </div>
    </div>
  );
}

const floatCard = "lift flex w-full max-w-[340px] flex-col gap-3 rounded-[18px] bg-surface p-5 shadow-float";

export function LandingView() {
  const weather = useQuery(weatherOptions());
  const metrics = useQuery(metricsOptions());
  const ready = useQuery(readyOptions());
  const bus = useQuery(incidentsOptions("bus"));
  const city = useQuery(incidentsOptions("city"));
  const road = useQuery(incidentsOptions("road"));
  const street = useQuery(incidentsOptions("street"));

  const wx = weather.data?.wx ?? "clear";
  const m = metrics.isSuccess ? metrics.data : undefined;
  // Different real incidents per section (hero, step 3, step 2) so no sentence repeats on the page.
  const pool = rankDistinct([bus.data, city.data, road.data, street.data]);
  const top = pool[0];
  const foresee = pool.find((i) => i.id !== top?.id && i.what_next !== top?.what_next) ?? top;
  // City footage only (the frame is a city crossing): riskiest live city moment that has a measured gap.
  const withGap = (city.data ?? []).filter((i) => !i.fixture && gapSummary(i.gap_series) !== null);
  const gap = withGap.find((i) => i.id !== top?.id && i.id !== foresee?.id) ?? topIncident([withGap]);
  const score = bestScore(m);
  const ran = m?.filter((x) => x.candidates > 0) ?? [];
  // Live results come from the bus safety run, or the city run until the bus run exists.
  const resultRun = ran.find((x) => x.mode === "bus") ?? ran.find((x) => x.mode === "city");
  const resultIncidents = ((resultRun?.mode === "bus" ? bus.data : city.data) ?? []).filter((i) => !i.fixture);
  const totalWatched = ran.reduce((a, x) => a + x.candidates, 0);
  const totalRuledOut = ran.reduce((a, x) => a + x.ruled_out, 0);
  const stored = ready.data?.store ? STORE_LABEL[ready.data.store] : null;

  return (
    <div className="bg-ground">
      {/* Hero: the sky follows live London weather. */}
      <section className={cn(`wx-${wx}`, "sky-wash relative flex flex-col items-center px-4 pt-5 pb-16 md:px-10 md:pb-24")}>
        {wx === "rain" && <div aria-hidden className="rain-streaks pointer-events-none absolute inset-0" />}
        <nav className="relative flex w-full flex-wrap items-center gap-3 md:gap-4">
          <span className="font-serif text-2xl leading-none text-on-sky">
            Sixth<i className="text-on-sky-muted">Sense</i>
          </span>
          <WeatherPill />
          <div className="flex-1" />
          <span className="glass hidden h-8 items-center rounded-full px-3.5 text-[13px] font-medium lg:inline-flex">
            Built at the VAST Builders Challenge
          </span>
          <div className="hidden flex-1 lg:block" />
          <Button asChild size="sm" variant="glass" className="hidden sm:inline-flex">
            <Link href="/dashboard">Open the live map</Link>
          </Button>
        </nav>

        <div className="relative mt-12 flex flex-col items-center text-center md:mt-14">
          <h1 className="font-serif text-[clamp(44px,7vw,88px)] leading-[0.95] tracking-[-0.01em] text-balance text-on-sky">
            {BUS_COPY.heroTitle}
            <br />
            <i className="text-on-sky-muted">{BUS_COPY.heroItalic}</i>
          </h1>
          <p className="mt-5 max-w-[580px] text-[17px] leading-[1.45] text-on-sky md:text-lg">{BUS_COPY.heroSub}</p>
          <div className="mt-7 flex flex-col items-center gap-3 sm:flex-row">
            <Button asChild className="h-11 px-6">
              <Link href="/dashboard">Open the live map</Link>
            </Button>
            <Button asChild variant="glass" className="h-11 px-6">
              <a href="#how">How it works</a>
            </Button>
          </div>
          {score && (
            // Live: latest run with the most checked predictions (GET /api/metrics).
            <p className="mt-4 text-data text-on-sky-muted">{proofLine(score)}</p>
          )}
          <a
            href={BUS_COPY.visionZeroUrl}
            target="_blank"
            rel="noreferrer"
            className="mt-2 text-body-sm text-on-sky underline decoration-on-sky-muted underline-offset-4 hover:decoration-on-sky"
          >
            {BUS_COPY.visionZero}
          </a>
        </div>

        <HeroStage top={top} frame={FRAMES.hero} />
      </section>

      <BuiltWith />

      {/* How it works */}
      <section id="how" className="mx-auto flex max-w-[1200px] scroll-mt-6 flex-col gap-20 px-4 py-16 md:gap-24 md:px-10 md:py-24 lg:px-[80px]">
        <FeatureRow
          index={0}
          wash="sky-card"
          visual={
            <div className={floatCard}>
              <LiveLines />
              {ran.length > 0 && (
                <>
                  <div className="text-eye">Last runs</div>
                  {ran.map((x) => (
                    <div key={x.mode} className="flex items-center justify-between gap-3 text-body-sm">
                      <span>{MODE_INFO[x.mode].place}</span>
                      <span className="text-data whitespace-nowrap text-ink-muted">{x.candidates} clips</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          }
        />
        <FeatureRow
          index={1}
          wash="lav-card"
          visual={
            <div className={floatCard}>
              <GapCreative series={gap?.gap_series} frame={FRAMES.ruleOut} />
              {gap && <div className="text-data text-ink-muted">{gapLine(gapSummary(gap.gap_series)!)}</div>}
              {/* Live: sum of ruled_out / candidates over each mode's latest run. */}
              {totalWatched > 0 && (
                <div className="text-body-sm text-ink">
                  {totalRuledOut} of {totalWatched} alarms never reached a screen.
                </div>
              )}
            </div>
          }
        />
        <FeatureRow
          index={2}
          wash="dusk-card"
          visual={
            <Reveal className="lift zoom-img w-full max-w-[340px] overflow-hidden rounded-[18px] bg-surface shadow-float">
              <Frame frame={FRAMES.predict} className="aspect-video" />
              {foresee && (
                <div className="flex flex-col gap-1.5 px-[18px] py-3.5">
                  <div className={cn("text-title", rise)} style={stagger(1)}>{hazardOf(foresee)}</div>
                  <p className={cn("font-serif text-xl leading-[1.2]", rise)} style={stagger(2)}>
                    {foresee.what_next}
                  </p>
                  {foresee.fix && (
                    <p className={cn("text-body-sm text-ink-muted", rise)} style={stagger(3)}>
                      <b className="font-medium text-ink">{COPY.fix}</b> {foresee.fix}
                    </p>
                  )}
                  <div className={rise} style={stagger(4)}>
                    <StatusPill tone={riskTone(foresee.risk)}>{riskLabel(foresee.risk)}</StatusPill>
                  </div>
                </div>
              )}
            </Reveal>
          }
        />
        <FeatureRow
          index={3}
          wash="sky-card"
          visual={
            <div className={floatCard}>
              <div className="text-eye">One moment, start to finish</div>
              <CheckTimeline />
              {score ? (
                <div className="flex items-center gap-3 border-t border-hairline pt-3">
                  <ScoreBar metrics={score} />
                  <span className="text-body-sm text-ink">{scoreLine(score)} · {MODE_INFO[score.mode].name}</span>
                </div>
              ) : (
                <p className="text-body-sm text-ink-muted">{COPY.scoreNothingBody}</p>
              )}
            </div>
          }
        />
      </section>

      {/* Live results: real numbers only; hidden when metrics fail or no run exists. */}
      {resultRun && <LiveResults metrics={resultRun} incidents={resultIncidents} />}

      <section className="bg-surface px-4 py-16 text-center md:px-10 md:py-24">
        <Reveal>
          <p className={cn("mx-auto max-w-[1040px] font-serif text-[36px] leading-[1.08] text-ink md:text-[56px]", rise)}>
            Most camera footage is never watched. The few seconds that matter deserve a second look.
          </p>
        </Reveal>
      </section>

      <section className="mx-auto grid max-w-[1200px] grid-cols-1 gap-6 px-4 py-16 md:grid-cols-3 md:px-10 md:py-24 lg:px-[80px]">
        {AUDIENCES.map((a, n) => (
          <Reveal key={a.title} className="h-full">
            <div className={cn("lift flex h-full flex-col gap-2.5 rounded-xl bg-surface p-7 shadow-float", rise)} style={stagger(n)}>
              <div className="font-serif text-[28px] leading-tight">{a.title}</div>
              <p className="text-body-sm text-ink-muted">{a.body}</p>
              {n === 0 && <ReportStack />}
              {n === 1 && <MapTile />}
              {n === 2 && <CoachFan />}
            </div>
          </Reveal>
        ))}
      </section>

      <Team />

      <section className="px-4 pb-10 md:px-10">
        <div className="dusk-card flex flex-col items-center gap-6 rounded-xl px-6 py-16 text-center md:px-10 md:py-24">
          <p className="font-serif text-[40px] leading-[1.02] text-ink md:text-[56px]">
            Every bus on one map,
            <br />
            <i>the ones that need a look first.</i>
          </p>
          <p className="max-w-[620px] text-body-sm text-ink-muted">{BUS_COPY.honest}</p>
          <Button asChild size="lg" className="px-7">
            <Link href="/dashboard">Open the live map</Link>
          </Button>
        </div>
      </section>

      <footer className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 pt-6 pb-10 text-body-sm text-ink-muted md:px-10">
        <WordmarkLarge className="text-xl" />
        <div className="flex-1" />
        {stored && <span className="text-data">{stored}</span>}
        <a href="https://open-meteo.com/" target="_blank" rel="noreferrer" className="link-grow text-data">
          {COPY.weatherCredit}
        </a>
        <a href="https://tfl.gov.uk/info-for/open-data-users/" target="_blank" rel="noreferrer" className="link-grow text-data">
          {BUS_COPY.poweredBy}
        </a>
        <span>Made in London, 17 October 2026</span>
        <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="link-grow text-ink">
          GitHub
        </a>
      </footer>
    </div>
  );
}
