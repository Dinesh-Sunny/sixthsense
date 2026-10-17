import { cn } from "@/lib/utils";

/** Frosted panel on the atmosphere (wireframe .panel). */
export function Panel({ className, ...props }: React.ComponentProps<"section">) {
  return <section className={cn("glass rounded-panel px-5 py-[18px] shadow-float", className)} {...props} />;
}

export function PanelHeading({ className, ...props }: React.ComponentProps<"h2">) {
  return (
    <h2
      className={cn("mb-3 text-[13px] leading-none font-medium tracking-[0.06em] text-ink-muted uppercase", className)}
      {...props}
    />
  );
}
