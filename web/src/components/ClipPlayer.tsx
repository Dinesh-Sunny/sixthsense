"use client";

import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { clipUrl } from "@/lib/api/client";
import { COPY } from "@/lib/copy";
import { cn } from "@/lib/utils";

function PlayMark({ large }: { large?: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        "pointer-events-none relative z-[1] grid place-items-center rounded-full bg-scrim",
        large ? "size-14" : "size-11",
      )}
    >
      <svg viewBox="0 0 16 16" className={large ? "size-5" : "size-4"}>
        <path d="M5 3l8 5-8 5z" fill="var(--on-sky)" />
      </svg>
    </span>
  );
}

/**
 * 16:9 media well. Streams the clip through /api/clip (206 ranges), never autoplays.
 * Skeleton until the first frame paints; "Try again" when the clip fails.
 */
export function ClipPlayer({
  source,
  fallbackLabel,
  label,
  overlay,
  controls = false,
  large = false,
}: {
  source: string | null;
  fallbackLabel: string;
  label?: string;
  overlay?: React.ReactNode;
  controls?: boolean;
  large?: boolean;
}) {
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);

  return (
    <div className="relative grid aspect-video place-items-center overflow-hidden bg-surface-sunk text-data text-ink-muted">
      {source && state !== "error" && (
        <video
          key={attempt}
          className="absolute inset-0 size-full object-cover"
          src={clipUrl(source)}
          preload="metadata"
          muted
          playsInline
          controls={controls}
          aria-label={label}
          onLoadedData={() => setState("ready")}
          onError={() => setState("error")}
        />
      )}
      {source && state === "loading" && <Skeleton className="absolute inset-0 rounded-none" />}
      {!source && <span className="px-6 text-center">{fallbackLabel}</span>}
      {source && state === "error" && (
        <span className="relative z-[1] px-6 text-center text-body-sm font-sans text-ink-muted">
          {COPY.clipWontPlay}
          <br />
          <button
            type="button"
            className="text-ink underline underline-offset-2"
            onClick={() => {
              setState("loading");
              setAttempt((a) => a + 1);
            }}
          >
            {COPY.tryAgain}
          </button>
        </span>
      )}
      {source && state === "ready" && !controls && <PlayMark large={large} />}
      {overlay && <div className="absolute top-2.5 left-2.5 z-[1]">{overlay}</div>}
    </div>
  );
}
