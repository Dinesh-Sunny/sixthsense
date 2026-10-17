"use client";

import { useQuery } from "@tanstack/react-query";
import { readyOptions } from "@/lib/api/queries";
import { COPY, STORE_LABEL } from "@/lib/copy";

export function SiteFooter() {
  const { data } = useQuery(readyOptions());
  const stored = data?.store ? STORE_LABEL[data.store] : null;
  return (
    <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-6 text-data text-ink-muted md:px-8">
      {stored && <span>{stored}</span>}
      <a href="https://open-meteo.com/" className="underline-offset-2 hover:underline" rel="noreferrer" target="_blank">
        {COPY.weatherCredit}
      </a>
    </footer>
  );
}
