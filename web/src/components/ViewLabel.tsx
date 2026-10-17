import { StatusPill } from "@/components/StatusPill";
import type { Mode } from "@/lib/api/types";
import { STAND_IN_NOTE, VIEW_LABEL, viewOf } from "@/lib/incident";

/** "Front camera" / "Nearside camera" pill for clips from the bus views; nothing for other footage. */
export function ViewLabel({ incident, className }: { incident: { mode: Mode }; className?: string }) {
  const view = viewOf(incident);
  if (!view) return null;
  return (
    <StatusPill tone="unk" className={className ?? "bg-surface"}>
      {VIEW_LABEL[view]}
    </StatusPill>
  );
}

/** The honest stand-in line shown under every bus-view clip. */
export function StandInNote({ incident }: { incident: { mode: Mode } }) {
  if (!viewOf(incident)) return null;
  return <p className="text-data text-ink-muted">{STAND_IN_NOTE}</p>;
}
