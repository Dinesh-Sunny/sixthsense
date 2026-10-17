"use client";

import { useState } from "react";
import { apiUrl } from "@/lib/api/client";
import type { Incident } from "@/lib/api/types";
import { VIEW_LABEL, viewOf } from "@/lib/incident";
import { assetUrl, cn } from "@/lib/utils";

export interface StaticFrame {
  src: string;
  alt: string;
}

/**
 * A still from a real incident's clip: a muted, inert <video> seeked to 1 s (first frame via the clip proxy).
 * Falls back to the static JPG only when there is no incident or the clip can't load.
 */
export function ClipFrame({
  incident,
  fallback,
  className,
  showView = true,
}: {
  incident: Incident | undefined;
  fallback: StaticFrame;
  className?: string;
  showView?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const source = incident?.source;
  const view = viewOf(incident);
  const live = Boolean(source) && !failed;
  return (
    <div className={cn("relative size-full overflow-hidden", className)}>
      {live ? (
        <video
          className="block size-full object-cover"
          src={`${apiUrl("/clip", { source: source! })}#t=1`}
          preload="metadata"
          muted
          playsInline
          tabIndex={-1}
          aria-label={view ? `${VIEW_LABEL[view]} still from a real clip` : "Still from a real clip"}
          onError={() => setFailed(true)}
        />
      ) : (
        <img src={assetUrl(fallback.src)} alt={fallback.alt} className="block size-full object-cover" />
      )}
      {live && view && showView && (
        <span className="absolute top-2 left-2 rounded-full bg-scrim px-2 py-0.5 text-[11px] font-medium text-on-sky">
          {VIEW_LABEL[view]}
        </span>
      )}
    </div>
  );
}
