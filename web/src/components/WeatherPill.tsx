"use client";

import { useQuery } from "@tanstack/react-query";
import { weatherOptions } from "@/lib/api/queries";
import type { Wx } from "@/lib/api/types";
import { weatherText } from "@/lib/copy";

function WxIcon({ wx }: { wx: Wx }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round" as const };
  if (wx === "clear")
    return (
      <svg viewBox="0 0 16 16" className="size-3.5 text-risk-mid" aria-hidden>
        <circle cx="8" cy="8" r="3.2" {...common} />
        <path d="M8 1.5v1.6M8 12.9v1.6M1.5 8h1.6M12.9 8h1.6M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M3.4 12.6l1.1-1.1M11.5 4.5l1.1-1.1" {...common} />
      </svg>
    );
  if (wx === "night")
    return (
      <svg viewBox="0 0 16 16" className="size-3.5 text-slate" aria-hidden>
        <path d="M12.5 10.2A5 5 0 0 1 5.8 3.5a5 5 0 1 0 6.7 6.7z" {...common} />
      </svg>
    );
  return (
    <svg viewBox="0 0 16 16" className="size-3.5 text-slate" aria-hidden>
      <path d="M4.5 11.5h7a2.5 2.5 0 0 0 .3-5 3.5 3.5 0 0 0-6.8.6A2.2 2.2 0 0 0 4.5 11.5z" {...common} />
      {wx === "rain" && <path d="M6 13.5l-.5 1M9 13.5l-.5 1" {...common} />}
    </svg>
  );
}

export function WeatherPill() {
  const { data, isError } = useQuery(weatherOptions());
  if (!data || isError) return null;
  return (
    <span className="glass inline-flex h-7 items-center gap-2 rounded-full px-3 text-xs font-medium text-ink">
      <WxIcon wx={data.wx} />
      {weatherText(data)}
    </span>
  );
}
