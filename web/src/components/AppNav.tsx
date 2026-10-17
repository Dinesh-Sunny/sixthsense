"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Wordmark } from "@/components/Wordmark";
import { NAV } from "@/lib/copy";
import { cn } from "@/lib/utils";

/** Shared top bar for every inside page: Live map · Reports · Coaching · How it works. */
export function AppNav({ right, className, onSky = false }: { right?: React.ReactNode; className?: string; onSky?: boolean }) {
  const path = usePathname();
  return (
    <header className={cn("flex flex-wrap items-center gap-x-5 gap-y-3 px-4 py-4 md:px-8", className)}>
      <Link href="/" aria-label="SixthSense home">
        <Wordmark onSky={onSky} />
      </Link>
      <nav aria-label="Main" className="glass-map flex max-w-full gap-0.5 overflow-x-auto rounded-full p-1 shadow-float">
        {NAV.map((n) => {
          const here = path?.replace(/\/$/, "") || "/";
          const active = !("hash" in n) && (here === n.path || (n.path === "/reports" && here.startsWith("/incident")));
          return (
            <Link
              key={n.label}
              href={"hash" in n ? { pathname: n.path, hash: n.hash } : n.path}
              aria-current={active ? "page" : undefined}
              className={cn(
                "inline-flex h-8 shrink-0 items-center rounded-full px-3.5 text-[13px] font-medium whitespace-nowrap text-ink-muted transition-colors duration-150 hover:text-ink",
                active && "bg-surface text-ink shadow-[0_0_0_1px_var(--hairline)]",
              )}
            >
              {n.label}
            </Link>
          );
        })}
      </nav>
      <div className="flex-1" />
      {right}
    </header>
  );
}
