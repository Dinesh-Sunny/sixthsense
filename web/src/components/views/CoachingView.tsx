"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { Atmosphere } from "@/components/Atmosphere";
import { SiteFooter } from "@/components/SiteFooter";
import { LostPanel } from "@/components/StatePanels";
import { StatusPill } from "@/components/StatusPill";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { allIncidentsOptions, pairingsOptions } from "@/lib/api/queries";
import type { Incident, Pairing } from "@/lib/api/types";
import { BUS_COPY, plural, riskLabel, riskTone } from "@/lib/copy";

interface RouteCard {
  route: string;
  items: { pairing: Pairing; incident: Incident | undefined }[];
}

function groupByRoute(pairings: Pairing[], incidents: Map<string, Incident>): RouteCard[] {
  const byRoute = new Map<string, RouteCard>();
  for (const p of pairings) {
    const card = byRoute.get(p.route) ?? { route: p.route, items: [] };
    card.items.push({ pairing: p, incident: incidents.get(p.incident_id) });
    byRoute.set(p.route, card);
  }
  return [...byRoute.values()].sort(
    (a, b) => Math.max(...b.items.map((i) => i.pairing.risk)) - Math.max(...a.items.map((i) => i.pairing.risk)),
  );
}

export function CoachingView() {
  const pairings = useQuery(pairingsOptions());
  const incidents = useQuery(allIncidentsOptions());
  const byId = new Map((incidents.data ?? []).map((i) => [i.id, i]));
  const cards = groupByRoute(pairings.data ?? [], byId);

  return (
    <Atmosphere variant="soft">
      <AppNav />
      <main className="flex flex-col gap-6 px-4 pb-8 md:px-8">
        <div className="flex flex-col gap-2 pt-4">
          <h1 className="font-serif text-[40px] leading-none md:text-[56px]">Coaching by route</h1>
          <p className="max-w-[640px] text-body text-ink-muted">
            One card per route, built from the moments paired to its buses. Each fix is a coaching point for drivers on that route.
          </p>
          <p className="text-data text-ink-muted">Clips are stand-in footage paired to live buses for this demo.</p>
        </div>
        {pairings.isError ? (
          <LostPanel onRetry={() => void pairings.refetch()} />
        ) : pairings.isPending ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
            <Skeleton className="h-64 rounded-xl" />
            <Skeleton className="h-64 rounded-xl" />
          </div>
        ) : cards.length === 0 ? (
          <p className="text-body text-ink-muted">No routes have moments yet. Coaching cards appear after the next run.</p>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
            {cards.map((c) => {
              const checked = c.items.filter((x) => x.pairing.came_true !== "unknown");
              const cameTrue = checked.filter((x) => x.pairing.came_true === "yes").length;
              const top = Math.max(...c.items.map((x) => x.pairing.risk));
              return (
                <article key={c.route} className="flex flex-col gap-4 rounded-xl bg-surface p-6 shadow-float">
                  <div className="flex items-center gap-3">
                    <h2 className="font-serif text-[32px] leading-none">Route {c.route}</h2>
                    <div className="flex-1" />
                    <StatusPill tone={riskTone(top)}>{riskLabel(top)}</StatusPill>
                  </div>
                  <p className="text-data text-ink-muted">
                    {plural(c.items.length, "moment")} · {cameTrue} of {checked.length} predictions came true
                  </p>
                  <ul className="flex flex-col gap-3">
                    {c.items.map(({ pairing: p, incident: i }) => (
                      <li key={p.incident_id} className="flex flex-col gap-1 border-t border-hairline pt-3">
                        <span className="text-body-sm">{i?.what_next ?? "Moment details are loading."}</span>
                        {i?.fix && (
                          <span className="text-body-sm text-ink-muted">
                            <b className="font-medium text-ink">Coach</b> {i.fix}
                          </span>
                        )}
                        <Link
                          href={{ pathname: "/incident", query: { id: p.incident_id } }}
                          className="text-data text-slate underline-offset-2 hover:underline"
                        >
                          {BUS_COPY.openReport} →
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <Button asChild size="sm" variant="glass" className="mt-auto self-start">
                    <Link href={{ pathname: "/dashboard", query: { route: c.route } }}>{BUS_COPY.showOnMap}</Link>
                  </Button>
                </article>
              );
            })}
          </div>
        )}
      </main>
      <SiteFooter />
    </Atmosphere>
  );
}
