import { cn } from "@/lib/utils";

/** "Sixth" upright + "Sense" italic. */
export function Wordmark({ onSky = false, className }: { onSky?: boolean; className?: string }) {
  return (
    <span className={cn("font-serif text-2xl leading-none", onSky ? "text-on-sky" : "text-ink", className)}>
      Sixth<i className={onSky ? "text-on-sky-muted" : undefined}>Sense</i>
    </span>
  );
}
