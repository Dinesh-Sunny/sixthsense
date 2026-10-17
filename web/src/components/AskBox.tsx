"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { incidentHref } from "@/components/IncidentCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { askFootage } from "@/lib/api/queries";
import type { AskEvidence } from "@/lib/api/types";
import { COPY, clock } from "@/lib/copy";

const QUESTION_MAX = 500;

function citeText(e: AskEvidence): string | null {
  if (typeof e.camera_id !== "string" || !e.camera_id) return null;
  return typeof e.start_s === "number" ? `${e.camera_id} · ${clock(e.start_s)}` : e.camera_id;
}

/** Five states from Ask.dc.html: idle, thinking, answer, nothing found, can't reach. */
export function AskBox({ showChips = true }: { showChips?: boolean }) {
  const [question, setQuestion] = useState("");
  const ask = useMutation({ mutationFn: (q: string) => askFootage({ question: q }) });

  const submit = (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || ask.isPending) return;
    setQuestion(trimmed);
    ask.mutate(trimmed);
  };

  const answer = ask.data?.answer?.trim() ?? "";
  const cites = (ask.data?.evidence ?? []).map(citeText).filter((c): c is string => Boolean(c));
  const links = (ask.data?.evidence ?? []).filter((e) => typeof e.incident_id === "string").slice(0, 3);

  return (
    <div className="flex flex-col gap-3">
      <form
        className="flex items-center gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit(question);
        }}
      >
        <label htmlFor="ask-input" className="sr-only">
          {COPY.askLabel}
        </label>
        <Input
          id="ask-input"
          value={question}
          maxLength={QUESTION_MAX}
          placeholder={COPY.askPlaceholder}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <Button type="submit" size="sm" disabled={ask.isPending}>
          {ask.isPending ? <span className="shimmer">{COPY.asking}</span> : COPY.ask}
        </Button>
      </form>

      {ask.isIdle && showChips && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-body-sm text-ink-muted">{COPY.askTry}</span>
          {COPY.askChips.map((chip) => (
            <Button key={chip} type="button" variant="glass" size="sm" onClick={() => submit(chip)}>
              {chip}
            </Button>
          ))}
        </div>
      )}

      {ask.isPending && (
        <div className="flex flex-col gap-2" aria-live="polite">
          <p className="shimmer text-body-sm text-ink-muted">{COPY.askThinking}</p>
          <Skeleton className="h-3.5 w-[92%]" />
          <Skeleton className="h-3.5 w-[64%]" />
        </div>
      )}

      {ask.isSuccess && (
        <div aria-live="polite" className="flex flex-col gap-3">
          <div className="rounded-md border border-hairline bg-surface px-4 py-3 text-sm leading-[21px]">
            {answer || COPY.askNothing}
            {answer && cites.length > 0 && (
              <span className="mt-1.5 block text-data text-ink-muted">{cites.join("  ·  ")}</span>
            )}
          </div>
          {answer && links.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {links.map((e) => (
                <Button key={e.incident_id} asChild variant="glass" size="sm">
                  <Link href={incidentHref(e.incident_id as string)}>
                    {COPY.view} {typeof e.camera_id === "string" ? e.camera_id : ""}
                  </Link>
                </Button>
              ))}
            </div>
          )}
        </div>
      )}

      {ask.isError && (
        <div className="flex flex-col gap-3 rounded-md border border-risk-high bg-surface px-4 py-3" role="alert">
          <p className="text-body-sm text-ink">{COPY.askError}</p>
          <div>
            <Button size="sm" onClick={() => ask.mutate(question.trim())}>
              {COPY.tryAgain}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
