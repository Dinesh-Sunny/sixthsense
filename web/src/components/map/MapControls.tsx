"use client";

import { Popover } from "radix-ui";
import type { Layers, Scene, Theme } from "@/components/map/BusMap";
import { INVOLVED_LABEL, Icon, OUTCOME_LABEL, type Involved, type Outcome } from "@/components/map/icons";
import { MAP_COPY } from "@/components/map/mapCopy";
import { BUS_STATE, type BusState } from "@/lib/copy";
import { cn } from "@/lib/utils";

const SCENES: { id: Scene; label: string }[] = [
  { id: "2d", label: "2D" },
  { id: "3d", label: "3D" },
  { id: "drone", label: "Drone" },
];
const THEMES: { id: Theme; label: string }[] = [
  { id: "light", label: "Light" },
  { id: "dark", label: "Dark" },
  { id: "satellite", label: "Satellite" },
  { id: "night", label: "Night" },
];

function Choice<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { id: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-eye">{label}</div>
      <div role="radiogroup" aria-label={label} className="flex gap-0.5 rounded-full bg-surface-sunk p-1">
        {options.map((o) => (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={value === o.id}
            onClick={() => onChange(o.id)}
            className={cn(
              "h-7 flex-1 rounded-full px-2 text-xs font-medium text-ink-muted transition-colors duration-150 hover:text-ink",
              value === o.id && "bg-surface text-ink shadow-[0_0_0_1px_var(--hairline)]",
            )}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Check({ checked, label, onChange }: { checked: boolean; label: string; onChange: () => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 text-body-sm">
      {label}
      <input type="checkbox" checked={checked} onChange={onChange} className="size-4 accent-[var(--ink)]" />
    </label>
  );
}

const LEGEND_STATES: BusState[] = ["look", "watching", "filed"];
const LEGEND_OUTCOMES: Outcome[] = ["watching", "came-true", "missed"];
const LEGEND_INVOLVED: Involved[] = ["bike", "person", "car", "truck"];

function Legend() {
  return (
    <div className="flex flex-col gap-2 border-t border-hairline pt-3">
      <div className="text-eye">Legend</div>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs text-ink">
        {LEGEND_STATES.map((s) => (
          <li key={s} className="flex items-center gap-1.5">
            <span aria-hidden className="size-2.5 rounded-full" style={{ background: `var(${BUS_STATE[s].cssVar})` }} />
            {BUS_STATE[s].label}
          </li>
        ))}
        {LEGEND_OUTCOMES.map((o) => (
          <li key={o} className="flex items-center gap-1.5">
            <Icon name={o} className="size-3.5 text-ink-muted" />
            {OUTCOME_LABEL[o]}
          </li>
        ))}
        {LEGEND_INVOLVED.map((i) => (
          <li key={i} className="flex items-center gap-1.5">
            <Icon name={i} className="size-3.5 text-ink-muted" />
            {INVOLVED_LABEL[i]}
          </li>
        ))}
      </ul>
      <p className="text-data text-ink-muted">Numbers show the order to look at them.</p>
    </div>
  );
}

/** One "Map" button: view, layers and theme folded into a popover. */
export function MapControls({
  scene,
  theme,
  layers,
  onScene,
  onTheme,
  onLayers,
}: {
  scene: Scene;
  theme: Theme;
  layers: Layers;
  onScene: (s: Scene) => void;
  onTheme: (t: Theme) => void;
  onLayers: (l: Layers) => void;
}) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="glass-map inline-flex h-9 items-center gap-2 rounded-full px-3.5 text-[13px] font-medium text-ink shadow-float transition-colors duration-150 hover:bg-surface"
        >
          <svg viewBox="0 0 16 16" className="size-4 text-ink-muted" aria-hidden>
            <path d="M2 4l4-1.5 4 1.5 4-1.5v9.5L10 13.5 6 12 2 13.5z M6 2.5V12 M10 4v9.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          </svg>
          {MAP_COPY.map}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={8}
          className="glass-map z-50 flex w-[280px] flex-col gap-4 rounded-panel p-4 shadow-float outline-none"
        >
          <Choice label={MAP_COPY.view} value={scene} options={SCENES} onChange={onScene} />
          <div className="flex flex-col gap-2">
            <div className="text-eye">{MAP_COPY.layers}</div>
            <Check checked={layers.traffic} label={MAP_COPY.traffic} onChange={() => onLayers({ ...layers, traffic: !layers.traffic })} />
            <Check checked={layers.all} label={MAP_COPY.allBuses} onChange={() => onLayers({ ...layers, all: !layers.all })} />
          </div>
          <Choice label={MAP_COPY.theme} value={theme} options={THEMES} onChange={onTheme} />
          <Legend />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
