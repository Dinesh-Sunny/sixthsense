"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { Popover } from "radix-ui";
import { useState } from "react";
import { MAP_COPY } from "@/components/map/mapCopy";
import { Skeleton } from "@/components/ui/skeleton";
import { askFootage } from "@/lib/api/queries";

const QUESTION_MAX = 500;

/** Small "Ask about the footage" field; answers open in a popover under it (POST /api/ask). */
export function AskFootage() {
  const [question, setQuestion] = useState("");
  const [open, setOpen] = useState(false);
  const ask = useMutation({ mutationFn: (q: string) => askFootage({ question: q }) });
  const links = (ask.data?.evidence ?? [])
    .filter((e): e is typeof e & { incident_id: string } => typeof e.incident_id === "string")
    .slice(0, 3);
  const answer = ask.data?.answer?.trim() ?? "";

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Anchor asChild>
        <form
          role="search"
          className="glass-map flex h-9 w-[240px] items-center gap-2 rounded-full px-3.5 shadow-float"
          onSubmit={(e) => {
            e.preventDefault();
            const q = question.trim();
            if (!q || ask.isPending) return;
            ask.mutate(q);
            setOpen(true);
          }}
        >
          <svg viewBox="0 0 16 16" className="size-4 shrink-0 text-ink-muted" aria-hidden>
            <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <label htmlFor="map-ask" className="sr-only">
            {MAP_COPY.ask}
          </label>
          <input
            id="map-ask"
            value={question}
            maxLength={QUESTION_MAX}
            placeholder={MAP_COPY.askPlaceholder}
            onChange={(e) => setQuestion(e.target.value)}
            className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-ink-muted"
          />
        </form>
      </Popover.Anchor>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={8}
          onOpenAutoFocus={(e) => e.preventDefault()}
          className="glass-map z-50 flex w-[320px] flex-col gap-3 rounded-panel p-4 shadow-float outline-none"
        >
          {ask.isPending && (
            <div className="flex flex-col gap-2" aria-live="polite">
              <p className="shimmer text-body-sm text-ink-muted">{MAP_COPY.asking}</p>
              <Skeleton className="h-3.5 w-[90%]" />
              <Skeleton className="h-3.5 w-[60%]" />
            </div>
          )}
          {ask.isError && <p className="text-body-sm text-risk-high">{MAP_COPY.askError}</p>}
          {ask.isSuccess && (
            <>
              <p className="text-body-sm text-ink" aria-live="polite">
                {answer || MAP_COPY.askNothing}
              </p>
              {answer &&
                links.map((e) => (
                  <Link
                    key={e.incident_id}
                    href={{ pathname: "/incident", query: { id: e.incident_id } }}
                    className="text-data text-slate underline-offset-2 hover:underline"
                  >
                    Open report{typeof e.camera_id === "string" ? ` · ${e.camera_id}` : ""} →
                  </Link>
                ))}
            </>
          )}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
