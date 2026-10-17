"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MODES, type Mode, type ModeMetrics } from "@/lib/api/types";
import { MODE_INFO } from "@/lib/copy";

export function ModeTabs({
  mode,
  metrics,
  onChange,
}: {
  mode: Mode;
  metrics: ModeMetrics[] | undefined;
  onChange: (m: Mode) => void;
}) {
  return (
    <Tabs value={mode} onValueChange={(v) => onChange(v as Mode)}>
      <TabsList aria-label="Camera mode">
        {MODES.map((m) => {
          const row = metrics?.find((x) => x.mode === m);
          return (
            <TabsTrigger key={m} value={m}>
              {MODE_INFO[m].name}
              {row && <span className="font-mono text-[11px] leading-none text-ink-muted">{row.verified}</span>}
            </TabsTrigger>
          );
        })}
      </TabsList>
    </Tabs>
  );
}
