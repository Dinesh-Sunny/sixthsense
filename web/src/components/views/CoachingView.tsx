"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { Atmosphere } from "@/components/Atmosphere";
import { ReportRow, ReportRowSkeleton } from "@/components/ReportRow";
import { SiteFooter } from "@/components/SiteFooter";
import { LostPanel } from "@/components/StatePanels";
import { StatusPill } from "@/components/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { allIncidentsOptions, pairingsOptions } from "@/lib/api/queries";
import type { Incident, Pairing } from "@/lib/api/types";
import { COACHING_COPY, REPORT_COPY, plural, riskLabel, riskTone } from "@/lib/copy";
import { hazardOf, inModes, useDataModes } from "@/lib/incident";
import { useSignedOff } from "@/lib/signoff";

interface RouteGroup {
  route: string;
  items: { pairing: Pairing; incident: Incident | undefined }[];
  top: number;
}

function groupByRoute(pairings: Pairing[], incidents: Map<string, Incident>): RouteGroup[] {
  const byRoute = new Map<string, RouteGroup>();
  for (const p of pairings) {
    const g = byRoute.get(p.route) ?? { route: p.route, items: [], top: 0 };
    g.items.push({ pairing: p, incident: incidents.get(p.incident_id) });
    g.top = Math.max(g.top, p.risk);
    byRoute.set(p.route, g);
  }
  for (const g of byRoute.values()) g.items.sort((a, b) => b.pairing.risk - a.pairing.risk);
  return [...byRoute.values()].sort((a, b) => b.top - a.top || a.route.localeCompare(b.route, "en", { numeric: true }));
}

function mostCommon(values: string[]): [string, number] | null {
  const counts = new Map<string, number>();
  for (const v of values) if (v) counts.set(v, (counts.get(v) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0] ?? null;
}

/** The route's pattern by hazard type, e.g. "Cyclist on the nearside, 3 times on route 18". */
function patternLine(g: RouteGroup): string {
  const known = g.items.map((x) => x.incident).filter((i): i is Incident => Boolean(i));
  const top = mostCommon(known.map((i) => hazardOf(i)));
  if (!top) return `${plural(g.items.length, "moment")} on route ${g.route}`;
  const [hazard, n] = top;
  return n > 1 ? `${hazard}, ${n} times on route ${g.route}` : `${hazard} on route ${g.route}`;
}

function scoreLineFor(g: RouteGroup): string {
  const checked = g.items.filter((x) => x.pairing.came_true !== "unknown");
  const yes = checked.filter((x) => x.pairing.came_true === "yes").length;
  const lead = plural(g.items.length, "clip");
  return checked.length > 0 ? `${lead} · ${yes} of ${checked.length} came true` : `${lead} · not checked yet`;
}

/** The habit to try: the fix that comes up most often on this route. */
function habit(g: RouteGroup): string | null {
  return mostCommon(g.items.map((x) => x.incident?.fix ?? ""))?.[0] ?? null;
}

function PromiseLine() {
  return <p className="text-body-sm text-ink-muted">{COACHING_COPY.promise}</p>;
}

function RouteCard({ group: g }: { group: RouteGroup }) {
  return (
    <li className="group relative flex flex-col gap-3 rounded-lg border border-hairline bg-surface p-6 transition-colors duration-150 hover:border-ink-muted has-[a:focus-visible]:ring-[3px] has-[a:focus-visible]:ring-ring/50">
      <div className="flex items-center gap-3">
        <h2 className="font-serif text-[30px] leading-none">
          <Link
            href={{ pathname: "/coaching", query: { route: g.route } }}
            className="outline-none after:absolute after:inset-0 after:rounded-lg after:content-['']"
          >
            Route {g.route}
          </Link>
        </h2>
        <div className="flex-1" />
        <StatusPill tone={riskTone(g.top)}>{riskLabel(g.top)}</StatusPill>
      </div>
      <p className="text-body-sm text-ink">{patternLine(g)}</p>
      <div className="mt-auto flex items-center justify-between gap-3 text-data text-ink-muted">
        <span>{scoreLineFor(g)}</span>
        <span aria-hidden className="transition-transform duration-150 group-hover:translate-x-0.5">
          →
        </span>
      </div>
    </li>
  );
}

function RouteList({ groups }: { groups: RouteGroup[] }) {
  return (
    <>
      <div className="flex flex-col gap-2">
        <h1 className="font-serif text-[40px] leading-none md:text-[52px]">{COACHING_COPY.title}</h1>
        <p className="text-body-sm text-ink-muted">{COACHING_COPY.sub}</p>
      </div>
      {groups.length === 0 ? (
        <p className="text-body text-ink-muted">{COACHING_COPY.none}</p>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {groups.map((g) => (
            <RouteCard key={g.route} group={g} />
          ))}
        </ul>
      )}
      <PromiseLine />
    </>
  );
}

function RouteDetail({ route, group }: { route: string; group: RouteGroup | undefined }) {
  const signed = useSignedOff();
  const tip = group ? habit(group) : null;
  return (
    <>
      <nav aria-label="Breadcrumb" className="text-body-sm text-ink-muted">
        <ol className="flex items-center gap-2">
          <li>
            <Link href="/coaching" className="rounded-sm underline-offset-2 outline-none hover:text-ink hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50">
              Coaching
            </Link>
          </li>
          <li aria-hidden>/</li>
          <li aria-current="page" className="text-ink">
            Route {route}
          </li>
        </ol>
      </nav>
      <div className="flex flex-wrap items-end gap-x-6 gap-y-4">
        <div className="flex w-full min-w-0 flex-col gap-2 sm:w-auto sm:flex-1">
          <h1 className="font-serif text-[40px] leading-none md:text-[52px]">Route {route}</h1>
          <p className="text-body text-ink">{group ? patternLine(group) : COACHING_COPY.unknownRoute(route)}</p>
          {group && <p className="text-data text-ink-muted">{scoreLineFor(group)}</p>}
        </div>
        <Button asChild variant="glass">
          <Link href={{ pathname: "/dashboard", query: { route } }}>{COACHING_COPY.showRoute}</Link>
        </Button>
      </div>
      {tip && (
        <section aria-labelledby="habit-h" className="flex flex-col gap-2 rounded-lg border border-hairline bg-surface p-6">
          <h2 id="habit-h" className="text-eye">
            {COACHING_COPY.habit}
          </h2>
          <p className="font-serif text-[24px] leading-[1.2] text-balance">{tip}</p>
        </section>
      )}
      {group && (
        <section aria-labelledby="clips-h" className="flex flex-col gap-3">
          <h2 id="clips-h" className="text-eye">
            {COACHING_COPY.clips}
          </h2>
          <ul className="flex flex-col gap-3">
            {group.items.map(({ pairing: p, incident: i }) =>
              i ? (
                <ReportRow key={p.incident_id} incident={i} pairing={p} signedOff={signed.has(i.id)} secondary="happened" />
              ) : (
                <ReportRowSkeleton key={p.incident_id} />
              ),
            )}
          </ul>
        </section>
      )}
      <PromiseLine />
    </>
  );
}

export function CoachingView() {
  const route = useSearchParams().get("route");
  const pairings = useQuery(pairingsOptions());
  const incidents = useQuery(allIncidentsOptions());
  const byId = new Map((incidents.data ?? []).map((i) => [i.id, i]));
  const dataModes = useDataModes();
  const groups = groupByRoute(inModes(pairings.data, dataModes), byId);

  return (
    <Atmosphere variant="soft">
      <AppHeader />
      <main className="mx-auto flex w-full max-w-[960px] flex-col gap-8 px-4 pt-6 pb-12 md:px-8 md:pt-10">
        {pairings.isError ? (
          <LostPanel onRetry={() => void pairings.refetch()} />
        ) : pairings.isPending ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2" aria-busy>
            <Skeleton className="h-40 rounded-lg" />
            <Skeleton className="h-40 rounded-lg" />
          </div>
        ) : route ? (
          <RouteDetail route={route} group={groups.find((g) => g.route === route)} />
        ) : (
          <RouteList groups={groups} />
        )}
        <p className="text-data text-ink-muted">{REPORT_COPY.standIn}</p>
      </main>
      <SiteFooter />
    </Atmosphere>
  );
}
