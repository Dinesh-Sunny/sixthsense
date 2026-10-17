import { cva } from "class-variance-authority";
import { Badge } from "@/components/ui/badge";
import { type Tone } from "@/lib/copy";
import { cn } from "@/lib/utils";

// Colour always comes with a word; the dot is decoration only.
const tone = cva("", {
  variants: {
    tone: {
      hi: "text-risk-high",
      mid: "text-risk-mid",
      lo: "text-risk-low",
      ok: "text-truth",
      unk: "text-slate",
      sample: "border-dashed text-ink-muted",
    },
  },
});

export function StatusPill({ tone: t, children, className }: { tone: Tone; children: React.ReactNode; className?: string }) {
  return (
    <Badge variant="outline" className={cn("font-sans", tone({ tone: t }), className)}>
      {t !== "sample" && <span aria-hidden className="size-1.5 rounded-full bg-current" />}
      {children}
    </Badge>
  );
}
