"use client";

import { useEffect, useRef, useState } from "react";
import { useInView } from "@/components/landing/reveal";
import { apiUrl, posterUrl } from "@/lib/api/client";
import { acquireVideoSlot } from "@/lib/videoSlots";
import { cn } from "@/lib/utils";

type Stage = "poster" | "video" | "failed";

/**
 * A still frame of a clip. Prefers the JPEG poster (GET /api/poster, lazy img); if that 404s, falls back to a
 * muted <video> seeked to 1 s, attached only once in view and through a 3-at-a-time loading queue.
 * Renders `fallback` when neither works.
 */
export function ClipStill({
  source,
  alt,
  className,
  fallback = null,
}: {
  source: string;
  alt: string;
  className?: string;
  fallback?: React.ReactNode;
}) {
  const [stage, setStage] = useState<Stage>("poster");
  const [ref, inView] = useInView<HTMLDivElement>(0.01);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const release = useRef<(() => void) | null>(null);

  // Video fallback: wait for view + a free slot, then attach the src.
  useEffect(() => {
    if (stage !== "video" || !inView || videoSrc) return;
    let cancelled = false;
    void acquireVideoSlot().then((free) => {
      if (cancelled) {
        free();
        return;
      }
      release.current = free;
      setVideoSrc(`${apiUrl("/clip", { source })}#t=1`);
    });
    return () => {
      cancelled = true;
    };
  }, [stage, inView, videoSrc, source]);

  // Free the slot if the still unmounts mid-load.
  useEffect(() => () => release.current?.(), []);

  const done = () => {
    release.current?.();
    release.current = null;
  };

  return (
    <div ref={ref} className={cn("relative size-full overflow-hidden bg-surface-sunk", className)}>
      {stage === "poster" && (
        <img
          src={posterUrl(source, 1)}
          alt={alt}
          loading="lazy"
          decoding="async"
          className="block size-full object-cover"
          onError={() => setStage("video")}
        />
      )}
      {stage === "video" && videoSrc && (
        <video
          className="block size-full object-cover"
          src={videoSrc}
          preload="metadata"
          muted
          playsInline
          tabIndex={-1}
          aria-label={alt}
          onLoadedData={done}
          onError={() => {
            done();
            setStage("failed");
          }}
        />
      )}
      {stage === "failed" && fallback}
    </div>
  );
}
