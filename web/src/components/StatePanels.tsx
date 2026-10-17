"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { COPY } from "@/lib/copy";
import { cn } from "@/lib/utils";

const panel = "glass flex-none items-start justify-start gap-4 rounded-panel border-solid p-7 text-left shadow-float md:p-7";

/** "All calm on I-24" (States.dc.html, empty camera). */
export function CalmPanel({ title, body }: { title: string; body: string }) {
  return (
    <Empty className={panel}>
      <EmptyHeader className="items-start text-left">
        <EmptyTitle className="font-serif text-[28px] leading-[1.15] font-normal">{title}</EmptyTitle>
        <EmptyDescription className="text-body-sm text-ink-muted">{body}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent className="items-start">
        <Button asChild variant="glass" size="sm">
          <Link href="/run">{COPY.watchAnother}</Link>
        </Button>
      </EmptyContent>
    </Empty>
  );
}

/** "We lost the connection" with Try again (States.dc.html). */
export function LostPanel({ onRetry, title = COPY.lostTitle, body = COPY.lostBody, className }: { onRetry: () => void; title?: string; body?: string; className?: string }) {
  return (
    <Empty className={cn(panel, "border-risk-high", className)} role="alert">
      <EmptyHeader className="items-start text-left">
        <EmptyTitle className="font-serif text-[28px] leading-[1.15] font-normal">{title}</EmptyTitle>
        <EmptyDescription className="text-body-sm text-ink-muted">{body}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent className="items-start">
        <Button size="sm" onClick={onRetry}>
          {COPY.tryAgain}
        </Button>
      </EmptyContent>
    </Empty>
  );
}
