"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { WeatherPill } from "@/components/WeatherPill";
import { Wordmark } from "@/components/Wordmark";
import { APP_NAV } from "@/lib/copy";
import { cn } from "@/lib/utils";

/** Which nav item owns a path: reports own their detail pages, coaching its route pages. */
function activeFor(path: string): string | null {
  if (path.startsWith("/incident") || path.startsWith("/reports") || path.startsWith("/run")) return "/reports";
  if (path.startsWith("/coaching")) return "/coaching";
  if (path.startsWith("/dashboard")) return "/dashboard";
  return null;
}

/** One top bar for every inside page: wordmark, Live · Reports · Coaching, weather. */
export function AppHeader({ className, right }: { className?: string; right?: React.ReactNode }) {
  const here = usePathname()?.replace(/\/$/, "") || "/";
  const active = activeFor(here);
  return (
    <header className={cn("flex items-center gap-x-3 gap-y-3 px-4 py-4 sm:gap-x-4 md:gap-x-6 md:px-8", className)}>
      <Link
        href="/"
        aria-label="SixthSense home"
        className="shrink-0 rounded-md outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        <Wordmark />
      </Link>
      <nav aria-label="Main" className="glass-map flex min-w-0 gap-0.5 overflow-x-auto rounded-full p-1 shadow-float">
        {APP_NAV.map((n) => {
          const on = active === n.path;
          return (
            <Link
              key={n.path}
              href={n.path}
              aria-current={on ? "page" : undefined}
              className={cn(
                "inline-flex h-8 shrink-0 items-center rounded-full px-2.5 text-[13px] font-medium whitespace-nowrap sm:px-3.5 text-ink-muted outline-none transition-colors duration-150 hover:bg-surface-sunk hover:text-ink focus-visible:ring-[3px] focus-visible:ring-ring/50",
                on && "bg-surface text-ink shadow-[0_0_0_1px_var(--hairline)] hover:bg-surface",
              )}
            >
              {n.label}
            </Link>
          );
        })}
      </nav>
      <div className="flex-1" />
      {/* Pages may swap the weather pill for their own tools (the live map shows weather in its bottom bar). */}
      {right ?? (
        <div className="hidden sm:block">
          <WeatherPill />
        </div>
      )}
    </header>
  );
}
