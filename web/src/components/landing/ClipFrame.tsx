"use client";

import { ClipStill } from "@/components/ClipStill";
import type { Incident } from "@/lib/api/types";
import { VIEW_LABEL, viewOf } from "@/lib/incident";
import { assetUrl, cn } from "@/lib/utils";

export interface StaticFrame {
  src: string;
  alt: string;
}

/**
 * A still from a real incident's clip (poster JPEG, else a lazy video frame at 1 s).
 * Falls back to the static JPG only when there is no incident or neither still loads.
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
  const source = incident?.source;
  const view = viewOf(incident);
  const staticImg = <img src={assetUrl(fallback.src)} alt={fallback.alt} className="block size-full object-cover" />;
  return (
    <div className={cn("relative size-full overflow-hidden", className)}>
      {source ? (
        <ClipStill
          source={source}
          alt={view ? `${VIEW_LABEL[view]} still from a real clip` : "Still from a real clip"}
          fallback={staticImg}
        />
      ) : (
        staticImg
      )}
      {source && view && showView && (
        <span className="absolute top-2 left-2 rounded-full bg-scrim px-2 py-0.5 text-[11px] font-medium text-on-sky">
          {VIEW_LABEL[view]}
        </span>
      )}
    </div>
  );
}
