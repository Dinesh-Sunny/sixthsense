"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { AccuracyMeter } from "@/components/AccuracyMeter";
import { GapChart } from "@/components/GapChart";
import { StatusPill } from "@/components/StatusPill";
import { WeatherPill } from "@/components/WeatherPill";
import { Button } from "@/components/ui/button";
import { incidentsOptions, metricsOptions, readyOptions, weatherOptions } from "@/lib/api/queries";
import { MODES, type Incident, type ModeMetrics } from "@/lib/api/types";
import { COPY, MODE_INFO, STORE_LABEL, VERDICT, cameraLine, gapLine, gapSummary, riskLabel, riskTone, scoreLine } from "@/lib/copy";
import { assetUrl, cn } from "@/lib/utils";

const GITHUB_URL = "https://github.com/Dinesh-Sunny/sixthsense";

// Real frames from the archive the agent watches (public/landing).
const FRAMES = {
  hero: { src: "/landing/f0.jpg", alt: "A San Francisco crossing seen from a street camera, people on the zebra crossing" },
  watch: { src: "/landing/f3.jpg", alt: "A city intersection seen from above, cars and people waiting to cross" },
  ruleOut: { src: "/landing/f6.jpg", alt: "The I-24 highway in Nashville from an overhead camera" },
  predict: { src: "/landing/f1.jpg", alt: "A New York crossing with pedestrians and a cyclist" },
};

const STACK = [
  { name: "VAST VastDB", role: "Keeps every moment, prediction and score, so the dashboard and the record are the same thing." },
  { name: "NVIDIA Cosmos3-Reason", role: "Watches each clip, says what happens next and why, then watches the next clip to check." },
  { name: "YOLO11 on CoreWeave", role: "Finds the cars and people in every frame, so close calls are measured, not guessed." },
  { name: "W&B Weave", role: "Records every model call and every score, so each prediction can be traced back." },
];

const STEPS = [
  {
    title: "It watches\nevery clip",
    body: "Highways, crossings, quiet streets. It searches the indexed footage for risky moments across every camera, so nothing waits for a person to press play.",
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
  { title: "Road operators", body: "See risky lane changes and braking before they turn into a pile-up." },
  { title: "City safety teams", body: "Find the crossings where drivers don't yield, with the clips to prove it." },
  { title: "Fleet insurers", body: "Know which moments were close calls, and which predictions held up." },
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

const floatCard = "flex w-full max-w-[340px] flex-col gap-3 rounded-[18px] bg-surface p-5 shadow-float";

export function LandingView() {
  const weather = useQuery(weatherOptions());
  const metrics = useQuery(metricsOptions());
  const ready = useQuery(readyOptions());
  const city = useQuery(incidentsOptions("city"));
  const road = useQuery(incidentsOptions("road"));
  const street = useQuery(incidentsOptions("street"));

  const wx = weather.data?.wx ?? "clear";
  const m = metrics.isSuccess ? metrics.data : undefined;
  const top = topIncident([city.data, road.data, street.data]);
  const gapSource = topIncident([road.data, city.data]);
  const gap = gapSource && gapSummary(gapSource.gap_series) ? gapSource : undefined;
  const score = bestScore(m);
  const ran = m?.filter((x) => x.candidates > 0) ?? [];
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
            <Link href="/dashboard">Open the dashboard</Link>
          </Button>
        </nav>

        <div className="relative mt-12 flex flex-col items-center text-center md:mt-14">
          <h1 className="font-serif text-[clamp(44px,7vw,88px)] leading-[0.95] tracking-[-0.01em] text-balance text-on-sky">
            See what happens next,
            <br />
            <i className="text-on-sky-muted">before it happens.</i>
          </h1>
          <p className="mt-5 max-w-[560px] text-[17px] leading-[1.45] text-on-sky md:text-lg">
            SixthSense watches your cameras, predicts the next few seconds, then checks the next clip to see if it was right.
          </p>
          <div className="mt-7 flex flex-col items-center gap-3 sm:flex-row">
            <Button asChild className="h-11 px-6">
              <Link href="/dashboard">Open the dashboard</Link>
            </Button>
            <Button asChild variant="glass" className="h-11 px-6">
              <a href="#how">How it works</a>
            </Button>
          </div>
          {score && (
            // Live: latest run with the most checked predictions (GET /api/metrics).
            <p className="mt-4 text-data text-on-sky-muted">{proofLine(score)}</p>
          )}
        </div>

        <div className="relative mt-10 w-full max-w-[1120px] md:mt-12">
          <div className="aspect-[16/9] overflow-hidden rounded-xl bg-surface-sunk shadow-float md:aspect-[16/8]">
            <Frame frame={FRAMES.hero} />
          </div>
          {top && (
            <div className="glass relative mx-auto -mt-10 flex w-[calc(100%-24px)] max-w-[380px] flex-col gap-2.5 rounded-panel bg-glass-strong p-5 shadow-float md:absolute md:right-10 md:-bottom-12 md:mt-0 md:w-[380px]">
              <div className="flex flex-wrap items-center gap-3">
                <StatusPill tone={riskTone(top.risk)}>{riskLabel(top.risk)}</StatusPill>
                <span className="text-data text-ink-muted">{cameraLine(top)}</span>
              </div>
              <div className="text-eye">{COPY.next}</div>
              <p className="font-serif text-[22px] leading-[1.2] text-balance md:text-2xl">{top.what_next}</p>
              <div className="flex items-center gap-3">
                <StatusPill tone={VERDICT[top.came_true].tone}>{VERDICT[top.came_true].label}</StatusPill>
                {top.came_true !== "unknown" && <span className="text-body-sm text-ink-muted">checked on the next clip</span>}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="mx-auto flex max-w-[1200px] scroll-mt-6 flex-col gap-20 px-4 py-16 md:gap-24 md:px-10 md:py-24 lg:px-[80px]">
        <FeatureRow
          index={0}
          wash="sky-card"
          visual={
            <div className={floatCard}>
              <div className="overflow-hidden rounded-sm">
                <Frame frame={FRAMES.watch} className="aspect-video" />
              </div>
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
              {gap ? (
                <>
                  <div className="text-eye">Gap in car lengths</div>
                  <GapChart series={gap.gap_series} />
                  <div className="text-data text-ink-muted">{gapLine(gapSummary(gap.gap_series)!)}</div>
                </>
              ) : (
                <div className="overflow-hidden rounded-sm">
                  <Frame frame={FRAMES.ruleOut} className="aspect-video" />
                </div>
              )}
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
            <div className="w-full max-w-[340px] overflow-hidden rounded-[18px] bg-surface shadow-float">
              <Frame frame={FRAMES.predict} className="aspect-video" />
              {top && (
                <div className="flex flex-col gap-1.5 px-[18px] py-3.5">
                  <div className="text-eye">{COPY.next}</div>
                  <p className="font-serif text-xl leading-[1.2]">{top.what_next}</p>
                  {top.fix && (
                    <p className="text-body-sm text-ink-muted">
                      <b className="font-medium text-ink">{COPY.fix}</b> {top.fix}
                    </p>
                  )}
                </div>
              )}
            </div>
          }
        />
        <FeatureRow
          index={3}
          wash="sky-card"
          visual={
            score ? (
              <div className={floatCard}>
                <div className="text-eye">Latest score · {MODE_INFO[score.mode].name}</div>
                <AccuracyMeter metrics={score} showLabel={false} />
                <div className="text-body-sm text-ink">{scoreLine(score)}</div>
              </div>
            ) : (
              <div className={floatCard}>
                <div className="text-eye">Score</div>
                <p className="text-body-sm text-ink-muted">{COPY.scoreNothingBody}</p>
              </div>
            )
          }
        />
      </section>

      {/* Live results: real numbers only; hidden when metrics fail. */}
      {ran.length > 0 && (
        <section className="mx-auto max-w-[1200px] px-4 pb-16 md:px-10 md:pb-24 lg:px-[80px]" aria-labelledby="results-h">
          <h2 id="results-h" className="mb-8 font-serif text-[36px] leading-[1.08] md:text-[44px]">
            Live results
          </h2>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {MODES.map((mode) => {
              const x = ran.find((r) => r.mode === mode);
              if (!x) return null;
              return (
                <div key={mode} className="flex flex-col gap-3 rounded-xl bg-surface p-7 shadow-float">
                  <div className="font-serif text-[28px] leading-none">{MODE_INFO[mode].name}</div>
                  <div className="text-body-sm text-ink-muted">{MODE_INFO[mode].place}</div>
                  <div className="font-mono text-[20px] leading-7 font-medium tabular-nums">{x.checked > 0 ? scoreLine(x) : "Nothing checked yet"}</div>
                  <div className="text-data text-ink-muted">
                    {x.candidates} clips watched · {x.ruled_out} ruled out · {x.verified} worth a look
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Built on */}
      <section className="mx-auto max-w-[1200px] px-4 pb-16 md:px-10 md:pb-24 lg:px-[80px]" aria-labelledby="stack-h">
        <h2 id="stack-h" className="mb-8 font-serif text-[36px] leading-[1.08] md:text-[44px]">
          Built on
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {STACK.map((s) => (
            <div key={s.name} className="flex flex-col gap-1.5 rounded-md border border-hairline bg-surface p-5">
              <div className="text-title">{s.name}</div>
              <p className="text-body-sm text-ink-muted">{s.role}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-surface px-4 py-16 text-center md:px-10 md:py-24">
        <p className="mx-auto max-w-[1040px] font-serif text-[36px] leading-[1.08] text-ink md:text-[56px]">
          Most camera footage is never watched. The few seconds that matter deserve a second look.
        </p>
      </section>

      <section className="mx-auto grid max-w-[1200px] grid-cols-1 gap-6 px-4 py-16 md:grid-cols-3 md:px-10 md:py-24 lg:px-[80px]">
        {AUDIENCES.map((a) => (
          <div key={a.title} className="flex flex-col gap-2.5 rounded-xl bg-surface p-7 shadow-float">
            <div className="font-serif text-[28px] leading-tight">{a.title}</div>
            <p className="text-body-sm text-ink-muted">{a.body}</p>
          </div>
        ))}
      </section>

      <section className="px-4 pb-10 md:px-10">
        <div className="dusk-card flex flex-col items-center gap-6 rounded-xl px-6 py-20 text-center md:px-10 md:py-[120px]">
          <p className="font-serif text-[40px] leading-[1.02] text-ink md:text-[56px]">
            Never leave your cameras
            <br />
            <i>home alone.</i>
          </p>
          <Button asChild size="lg" className="px-7">
            <Link href="/dashboard">Open the dashboard</Link>
          </Button>
        </div>
      </section>

      <footer className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 pt-6 pb-10 text-body-sm text-ink-muted md:px-10">
        <WordmarkLarge className="text-xl" />
        <div className="flex-1" />
        {stored && <span className="text-data">{stored}</span>}
        <a href="https://open-meteo.com/" target="_blank" rel="noreferrer" className="text-data underline-offset-2 hover:underline">
          {COPY.weatherCredit}
        </a>
        <span>Made in London, 17 October 2026</span>
        <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="text-ink underline-offset-2 hover:underline">
          GitHub
        </a>
      </footer>
    </div>
  );
}
