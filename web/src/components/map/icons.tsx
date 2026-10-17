// Our own tiny line icons (16px grid, 1.5px stroke) and a flat generic double-decker. No third-party icon art.
import type { Incident, Pairing } from "@/lib/api/types";

export type Involved = "bike" | "person" | "truck" | "car";
export type Outcome = "watching" | "came-true" | "missed";

type Shape = ["circle", { cx: number; cy: number; r: number }] | ["path", { d: string }];

const ICONS: Record<Involved | Outcome, Shape[]> = {
  bike: [
    ["circle", { cx: 4, cy: 11, r: 2.6 }],
    ["circle", { cx: 12, cy: 11, r: 2.6 }],
    ["path", { d: "M4 11l2.6-5h4.2L12 11M6.6 6L8 11h1.5M9.5 3.8h2" }],
  ],
  person: [
    ["circle", { cx: 8, cy: 3, r: 1.5 }],
    ["path", { d: "M8 5v4.5M8 6.5l-2.6 2M8 6.5l2.6 2M8 9.5l-2 4.5M8 9.5l2 4.5" }],
  ],
  truck: [
    ["path", { d: "M1.5 4h8v7h-8zM9.5 6.5h3l2 2.5V11h-5" }],
    ["circle", { cx: 4.5, cy: 12, r: 1.4 }],
    ["circle", { cx: 11.5, cy: 12, r: 1.4 }],
  ],
  car: [
    ["path", { d: "M2 10.5V8.5l1.6-3.5h8.8L14 8.5v2H2z" }],
    ["circle", { cx: 5, cy: 11.5, r: 1.3 }],
    ["circle", { cx: 11, cy: 11.5, r: 1.3 }],
  ],
  watching: [
    ["path", { d: "M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8z" }],
    ["circle", { cx: 8, cy: 8, r: 2 }],
  ],
  "came-true": [
    ["circle", { cx: 8, cy: 8, r: 6.2 }],
    ["path", { d: "M5.3 8.2l1.9 1.9 3.6-3.9" }],
  ],
  missed: [
    ["circle", { cx: 8, cy: 8, r: 6.2 }],
    ["path", { d: "M5.8 5.8l4.4 4.4M10.2 5.8l-4.4 4.4" }],
  ],
};

function shapeMarkup([tag, attrs]: Shape): string {
  return `<${tag} ${Object.entries(attrs)
    .map(([k, v]) => `${k}="${v}"`)
    .join(" ")}/>`;
}

export const INVOLVED_LABEL: Record<Involved, string> = { bike: "Cyclist", person: "Pedestrian", truck: "Truck or van", car: "Car" };
export const OUTCOME_LABEL: Record<Outcome, string> = { watching: "Watching", "came-true": "Came true", missed: "Didn't happen" };

/** SVG markup (for map markers built outside React). */
export function iconSvg(name: Involved | Outcome, size = 12): string {
  return `<svg viewBox="0 0 16 16" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name].map(shapeMarkup).join("")}</svg>`;
}

export function Icon({ name, className, title }: { name: Involved | Outcome; className?: string; title?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={className ?? "size-3.5"}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      {ICONS[name].map((shape, n) => (shape[0] === "circle" ? <circle key={n} {...shape[1]} /> : <path key={n} {...shape[1]} />))}
    </svg>
  );
}

/** Side view of a generic rounded double-decker, facing right; body takes the state colour. */
export function busSvg(body: string, glass: string, tyre: string): string {
  return `<svg viewBox="0 0 40 26" width="34" height="22" aria-hidden="true">
<rect x="1" y="1" width="36" height="20" rx="4.5" fill="${body}" stroke="white" stroke-width="1.2"/>
<rect x="4" y="3.5" width="6" height="5" rx="1.2" fill="${glass}"/><rect x="11.5" y="3.5" width="6" height="5" rx="1.2" fill="${glass}"/>
<rect x="19" y="3.5" width="6" height="5" rx="1.2" fill="${glass}"/><rect x="26.5" y="3.5" width="8" height="5" rx="1.5" fill="${glass}"/>
<rect x="4" y="11" width="6" height="4.5" rx="1.1" fill="${glass}"/><rect x="11.5" y="11" width="6" height="4.5" rx="1.1" fill="${glass}"/>
<rect x="27.5" y="11" width="7" height="5" rx="1.3" fill="${glass}"/>
<circle cx="9" cy="21.5" r="3.2" fill="${tyre}" stroke="white" stroke-width="1"/><circle cx="29" cy="21.5" r="3.2" fill="${tyre}" stroke="white" stroke-width="1"/>
</svg>`;
}

/** What's involved, from the incident's own words (plain keyword match; car when nothing else fits). */
export function involvedFrom(i: Incident | undefined): Involved {
  const text = `${i?.what_next ?? ""} ${i?.what_happens ?? ""} ${i?.type ?? ""} ${i?.description ?? ""}`.toLowerCase();
  if (/\b(cycl|bike|bicycl)/.test(text)) return "bike";
  if (/\b(pedestrian|person|people|woman|man|stroller|pram|walker|child)/.test(text)) return "person";
  if (/\b(truck|van|lorry|hgv)/.test(text)) return "truck";
  return "car";
}

export function outcomeOf(p: Pairing): Outcome {
  if (p.came_true === "yes" || p.came_true === "partly") return "came-true";
  if (p.came_true === "no") return "missed";
  return "watching";
}
