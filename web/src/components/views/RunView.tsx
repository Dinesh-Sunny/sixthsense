"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AccuracyMeter } from "@/components/AccuracyMeter";
import { AppHeader } from "@/components/AppHeader";
import { Atmosphere } from "@/components/Atmosphere";
import { Panel } from "@/components/Panel";
import { SiteFooter } from "@/components/SiteFooter";
import { LostPanel } from "@/components/StatePanels";
import { StatusPill } from "@/components/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { metricsOptions, queryKeys, runOptions, startRun } from "@/lib/api/queries";
import { MODES, type Mode, type RunStatus, type StepName, type StepProgress } from "@/lib/api/types";
import { COPY, MODE_INFO, REPORT_COPY, STEP_LABEL, STEP_ORDER, momentsHeadline, scoreDetail, watchingHeadline } from "@/lib/copy";
import { cn } from "@/lib/utils";

const RUN_LIMIT = 5;

/** Seconds until a new run may start (backend sends an ISO time). */
function useCooldown(until: string | null | undefined): number {
  const [now, setNow] = useState(() => Date.now());
  const target = until ? new Date(until).getTime() : 0;
  useEffect(() => {
    if (!target || target <= Date.now()) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [target]);
  return target > now ? Math.ceil((target - now) / 1000) : 0;
}

function StepRow({ name, step }: { name: StepName; step: StepProgress }) {
  const waiting = step.state === "pending";
  let status: React.ReactNode;
  if (step.state === "done") {
    status = <StatusPill tone="ok">Done · {step.done}{name === "rule_out" ? " out" : ""}</StatusPill>;
  } else if (step.state === "running") {
    status = (
      <StatusPill tone="unk">
        <span className="shimmer">{step.total > 0 ? `${step.done} of ${step.total}` : "Working"}</span>
      </StatusPill>
    );
  } else if (step.state === "error") {
    status = <StatusPill tone="hi">Stopped</StatusPill>;
  } else {
    status = <span className="text-data text-ink-muted">{COPY.waiting}</span>;
  }
  return (
    <div className={cn("flex items-center justify-between gap-3", waiting && "text-ink-muted")}>
      <span>{STEP_LABEL[name]}</span>
      {status}
    </div>
  );
}

function progress(run: RunStatus): number {
  const parts = STEP_ORDER.map((n) => {
    const s = run.steps[n];
    if (!s) return 0;
    if (s.state === "done") return 1;
    return s.total > 0 ? Math.min(1, s.done / s.total) : 0;
  });
  return parts.reduce((a, b) => a + b, 0) / STEP_ORDER.length;
}

const headingCls = "font-serif text-[28px] leading-[1.15]";
const stateCls = "font-mono text-[11px] leading-none font-medium tracking-[0.06em] text-slate uppercase";

export function RunView() {
  const queryClient = useQueryClient();
  const run = useQuery(runOptions());
  const metrics = useQuery(metricsOptions());
  const [mode, setMode] = useState<Mode>("road");
  const start = useMutation({
    mutationFn: () => startRun({ mode, limit: RUN_LIMIT }),
    onSuccess: (status) => queryClient.setQueryData(queryKeys.run, status),
  });

  // When a run finishes, the moments and the score change.
  const prev = useRef(run.data?.state);
  useEffect(() => {
    const now = run.data?.state;
    if (prev.current === "running" && now && now !== "running") {
      void queryClient.invalidateQueries({ queryKey: queryKeys.incidentsAll });
      void queryClient.invalidateQueries({ queryKey: queryKeys.metrics });
    }
    prev.current = now;
  }, [run.data?.state, queryClient]);

  const status = run.data;
  const running = status?.state === "running";
  const cooldown = useCooldown(status?.cooldown_until);
  const runsOff = status?.runs_enabled === false;
  const runMode = status?.mode ?? mode;
  const m = metrics.data?.find((x) => x.mode === runMode);
  const showWatching = status && status.state !== "idle" && status.mode;

  return (
    <Atmosphere variant="soft">
      <AppHeader />
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-2 px-4 pt-6 pb-8 md:px-8 md:pt-10">
        <nav aria-label="Breadcrumb" className="text-body-sm text-ink-muted">
          <Link href="/reports" className="rounded-sm underline-offset-2 outline-none hover:text-ink hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50">
            ← {REPORT_COPY.title}
          </Link>
        </nav>
        <h1 className="font-serif text-[40px] leading-none md:text-[52px]">{REPORT_COPY.checkFootage}</h1>
      </div>

      {run.isError && !status ? (
        <div className="mx-auto w-full max-w-[1200px] px-4 md:px-8">
          <LostPanel onRetry={() => void run.refetch()} />
        </div>
      ) : (
        <div className="mx-auto grid w-full max-w-[1200px] grid-cols-1 content-start gap-6 px-4 pb-12 md:px-8 lg:grid-cols-3">
          <section className="flex flex-col gap-3">
            <span className={stateCls}>1 · Pick what to watch</span>
            <Panel className="flex flex-col gap-4 p-6">
              <h2 className={headingCls}>{COPY.runPickTitle}</h2>
              <fieldset className="flex flex-col gap-2" disabled={running}>
                <legend className="sr-only">Camera</legend>
                {MODES.map((m2) => (
                  <label
                    key={m2}
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-3 rounded-md border bg-surface px-3.5 py-3 transition-colors duration-150",
                      mode === m2 ? "border-ink" : "border-hairline",
                    )}
                  >
                    <span>
                      <b className="font-medium">{MODE_INFO[m2].name}</b>
                      <br />
                      <span className="text-body-sm text-ink-muted">{MODE_INFO[m2].place}</span>
                    </span>
                    <input
                      type="radio"
                      name="mode"
                      value={m2}
                      checked={mode === m2}
                      onChange={() => setMode(m2)}
                      className="size-4 accent-[var(--ink)]"
                    />
                  </label>
                ))}
              </fieldset>
              <p className="text-body-sm text-ink-muted">{COPY.runPickHint}</p>
              {runsOff && <p className="text-body-sm text-ink-muted">{COPY.runsOff}</p>}
              {start.isError && <p className="text-body-sm text-risk-high">{COPY.runFailed}</p>}
              <Button
                className="self-start"
                disabled={running || runsOff || start.isPending || cooldown > 0 || run.isPending}
                onClick={() => start.mutate()}
              >
                {start.isPending ? COPY.runStarting : cooldown > 0 ? `Ready again in ${cooldown}s` : COPY.runStart}
              </Button>
            </Panel>
          </section>

          <section className="flex flex-col gap-3">
            <span className={stateCls}>2 · Watching</span>
            {run.isPending ? (
              <Skeleton className="h-64 rounded-panel" />
            ) : showWatching ? (
              <Panel className="flex flex-col gap-4 p-6" aria-live="polite">
                <h2 className={headingCls}>{watchingHeadline(status.mode as Mode)}</h2>
                <div className="flex flex-col gap-3">
                  {STEP_ORDER.map((n) =>
                    status.steps[n] ? <StepRow key={n} name={n} step={status.steps[n]} /> : null,
                  )}
                </div>
                <div className="h-1.5 rounded-full bg-surface-sunk" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress(status) * 100)}>
                  <div className="h-1.5 rounded-full bg-ink transition-[width] duration-150" style={{ width: `${Math.round(progress(status) * 100)}%` }} />
                </div>
                {status.state === "error" ? (
                  <p className="text-body-sm text-risk-high">{COPY.runFailed}</p>
                ) : (
                  running && <p className="text-body-sm text-ink-muted">{COPY.runLeave}</p>
                )}
              </Panel>
            ) : (
              <Panel className="p-6">
                <p className="text-body-sm text-ink-muted">Pick a camera and we&apos;ll show each step here as it happens.</p>
              </Panel>
            )}
          </section>

          <section className="flex flex-col gap-3">
            <span className={stateCls}>3 · Done</span>
            {status?.state === "done" && m ? (
              <Panel className="flex flex-col gap-4 p-6">
                <h2 className={headingCls}>{momentsHeadline(m.verified)}</h2>
                <AccuracyMeter metrics={m} showLabel={false} />
                <p className="text-body-sm text-ink-muted">{m.checked > 0 ? scoreDetail(m) : COPY.scoreNothingBody}</p>
                <Button asChild className="self-start">
                  <Link href="/reports">{COPY.runSee}</Link>
                </Button>
              </Panel>
            ) : (
              <Panel className="p-6">
                <p className="text-body-sm text-ink-muted">When we finish, your score and the moments worth a look show up here.</p>
              </Panel>
            )}
          </section>
        </div>
      )}
      <SiteFooter />
    </Atmosphere>
  );
}
