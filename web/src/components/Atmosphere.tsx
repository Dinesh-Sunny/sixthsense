"use client";

import { useQuery } from "@tanstack/react-query";
import { weatherOptions } from "@/lib/api/queries";
import { cn } from "@/lib/utils";

/**
 * Sets wx-* on the wrapper so the sky follows live London weather.
 * On error the sky stays clear (the :root default) and the pill hides itself.
 */
export function Atmosphere({
  variant,
  className,
  children,
}: {
  variant: "band" | "soft";
  className?: string;
  children: React.ReactNode;
}) {
  const { data } = useQuery(weatherOptions());
  const wx = data?.wx ?? "clear";
  return (
    <div className={cn(`wx-${wx}`, "relative min-h-dvh", variant === "band" ? "sky-band" : "sky-soft", className)}>
      {wx === "rain" && (
        <div aria-hidden className="rain-streaks pointer-events-none absolute inset-x-0 top-0 h-[440px]" />
      )}
      <div className="relative">{children}</div>
    </div>
  );
}
