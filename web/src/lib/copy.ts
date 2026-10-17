// All screen words and status colours live here (DESIGN.md + VOICE.md).
// Simple, precise, helpful, human. No pipeline words: those belong to HowItDecided.
import type { CameTrue, GapPoint, Incident, Mode, ModeMetrics, Pairing, StepName, StoreState, Weather, Wx } from "@/lib/api/types";

export type Tone = "hi" | "mid" | "lo" | "ok" | "unk" | "sample";

export function riskTone(risk: number): Tone {
  if (risk >= 4) return "hi";
  if (risk === 3) return "mid";
  return "lo";
}

export const riskLabel = (risk: number) => `Risk ${risk}`;

export const VERDICT: Record<CameTrue, { label: string; tone: Tone }> = {
  yes: { label: "Came true", tone: "ok" },
  partly: { label: "Partly", tone: "mid" },
  no: { label: "Didn't happen", tone: "hi" },
  unknown: { label: "Checking soon", tone: "unk" },
};

export const SAMPLE = { label: "Sample", tone: "sample" as Tone, example: "Example" };

export const MODE_INFO: Record<Mode, { name: string; place: string; where: string; calm: string }> = {
  road: {
    name: "Road",
    place: "I-24 highway, Nashville",
    where: "On I-24 in Nashville",
    calm: "All calm on I-24",
  },
  city: {
    name: "City",
    place: "6 intersections, New York and San Francisco",
    where: "Crossings in New York and San Francisco",
    calm: "All calm at the crossings",
  },
  street: {
    name: "Street",
    place: "One street, two full days",
    where: "One street over two full days",
    calm: "All calm on the street",
  },
};

export const STEP_LABEL: Record<StepName, string> = {
  find: "Finding risky moments",
  rule_out: "Ruling out false alarms",
  predict: "Predicting what's next",
  check: "Checking against the next clip",
};
export const STEP_ORDER: StepName[] = ["find", "rule_out", "predict", "check"];

export const WX_LABEL: Record<Wx, string> = {
  clear: "Sunny",
  cloudy: "Cloudy",
  rain: "Rain",
  night: "Clear night",
};

export function weatherText(w: Weather): string {
  const parts = [w.city];
  if (w.temp_c !== null && w.temp_c !== undefined) parts.push(`${Math.round(w.temp_c)}°`);
  parts.push(w.label || WX_LABEL[w.wx]);
  return parts.join(" · ");
}

export const STORE_LABEL: Record<StoreState, string | null> = {
  vast: "Saved in VastDB",
  json: "Saved locally",
  degraded: null,
};

export const COPY = {
  brand: "SixthSense",
  watchCamera: "Watch a camera",
  watchAnother: "Watch another camera",
  view: "View",
  allMoments: "All moments",
  riskiestFirst: "Riskiest first",
  next: "Next",
  why: "Why",
  now: "Now",
  fix: "Fix",
  prediction: "Prediction",
  whatHappened: "What happened next",
  checkedByWatching: "Checked by watching the next clip",
  notCheckedYet: "There's no next clip to check yet. We'll check as soon as one arrives.",
  nextStep: "Next step",
  sendAlert: "Send alert",
  copyLink: "Copy link",
  linkCopied: "Link copied",
  seeHow: "See how it decided",
  timeline: "Timeline",
  predictedHere: "Predicted here",
  checkedHere: "Checked here",
  whyTrust: "Why we trust it · gap in car lengths",
  ask: "Ask",
  askLabel: "Ask about today's footage",
  askPlaceholder: "Any close calls at a crossing?",
  asking: "Asking…",
  askThinking: "Looking through the footage…",
  askTry: "Try",
  askChips: ["Cars not yielding", "Cyclists near people"],
  askNothing: "No clips show that yet. Try different words, or watch another camera.",
  askError: "We can't reach the footage right now. Your question is saved.",
  tryAgain: "Try again",
  alertsSent: "Alerts sent",
  alertsNone: "No alerts sent yet. Send one from any moment.",
  howItWorks: "How it works",
  howItWorksBody:
    "It watches every clip, rules out false alarms, predicts the next few seconds, then checks the next clip to see if it was right.",
  lostTitle: "We lost the connection",
  lostBody: "Your moments are safe. We'll reconnect on our own, or you can try now.",
  clipWontPlay: "This clip can't play right now.",
  noClip: "No clip for this moment",
  sampleBody: "This is example data. Watch a camera to see real moments.",
  scoreNothing: "predictions checked so far",
  scoreNothingBody: "Each prediction gets checked against the clip that comes next. Scores appear as clips arrive.",
  scoreTitle: "Predictions checked against the next clip",
  notFound: "We couldn't find that moment.",
  notFoundBody: "It may be from an older run. Go back to see the latest moments.",
  weatherCredit: "Weather data by Open-Meteo.com",
  // Run page
  runPickTitle: "What should we watch?",
  runPickHint: "Takes a few minutes. You can leave while it works.",
  runStart: "Start watching",
  runStarting: "Starting…",
  runLeave: "You can leave this page. We'll keep going.",
  runSee: "See the moments",
  runFailed: "Something went wrong while watching. Your earlier moments are safe.",
  runBusy: "We're already watching a camera. Here's how it's going.",
  runsOff: "Watching is paused right now. Your moments are safe.",
  alertNotDelivered: "Saved, but the alert channel didn't answer.",
  waiting: "Waiting",
};

export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

export function momentsHeadline(n: number): string {
  if (n === 0) return "No moments need a look";
  return n === 1 ? "1 moment worth a look" : `${n} moments worth a look`;
}

export function watchingHeadline(mode: Mode): string {
  return mode === "city" ? "Watching 6 intersections" : mode === "road" ? "Watching I-24" : "Watching the street";
}

export function heroSubline(mode: Mode, m: ModeMetrics | undefined, sampleOnly: boolean): string {
  const lead = `${MODE_INFO[mode].where}.`;
  if (sampleOnly) return `${lead} Showing sample moments until a camera is watched.`;
  if (!m) return lead;
  return `${lead} ${plural(m.candidates, "clip")} watched, ${plural(m.ruled_out, "false alarm")} ruled out.`;
}

export function calmBody(m: ModeMetrics | undefined): string {
  if (!m) return "No moments yet. Watch a camera and we'll show anything that needs a look.";
  return `We watched ${plural(m.candidates, "clip")} and ruled out every alarm. We'll show moments here as soon as something needs a look.`;
}

/** "4 of 6 came true" (decision d7: yes / checked, partly counted on its own). */
export function scoreLine(m: ModeMetrics): string {
  return `${m.came_true_yes} of ${m.checked} came true`;
}

export function scoreDetail(m: ModeMetrics): string {
  const partly = m.came_true_partly > 0 ? ` ${m.came_true_partly} partly came true.` : "";
  const unchecked = Math.max(0, m.verified - m.checked);
  const waiting = unchecked > 0 ? ` ${unchecked} had no next clip yet.` : "";
  return `${m.came_true_yes} of ${m.checked} predictions came true when we checked the next clip.${partly}${waiting}`;
}

export function clock(s: number): string {
  const t = Math.max(0, Math.round(s));
  return `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
}

/** Camera language: `i24_cam-1 · 00:41-00:46` in data mono. */
export function cameraName(id: string | null | undefined): string {
  return id || "Camera";
}

export function cameraLine(i: Pick<Incident, "camera_id" | "start_s" | "end_s">): string {
  return `${cameraName(i.camera_id)} · ${clock(i.start_s)}-${clock(i.end_s)}`;
}

export function timeOfDay(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export interface GapSummary {
  from: number;
  to: number;
  seconds: number;
}

export function gapSummary(series: GapPoint[] | undefined): GapSummary | null {
  if (!series || series.length < 2) return null;
  const first = series[0];
  const low = series.reduce((a, b) => (b.cl < a.cl ? b : a), series[0]);
  if (low.cl >= first.cl) return null;
  return { from: first.cl, to: low.cl, seconds: Math.max(0, low.t - first.t) };
}

export function gapLine(g: GapSummary): string {
  return `Gap closed from ${g.from.toFixed(1)} to ${g.to.toFixed(1)} car lengths in ${g.seconds.toFixed(1)}s`;
}

export const CLOSE_CL = 1.5;

// ---- v2: London buses ----

export type BusState = "road" | "look" | "watching" | "filed";

/** One place for bus state: a paired bus is checked (filed), urgent (look) or being watched. */
export function busState(p: Pairing | undefined): BusState {
  if (!p) return "road";
  if (p.came_true !== "unknown") return "filed";
  return p.risk >= 4 ? "look" : "watching";
}

export const BUS_STATE: Record<BusState, { label: string; tone: Tone; cssVar: string }> = {
  road: { label: "On the road", tone: "unk", cssVar: "--bus" },
  look: { label: "Needs a look", tone: "hi", cssVar: "--risk-high" },
  watching: { label: "Watching", tone: "mid", cssVar: "--risk-mid" },
  filed: { label: "Report filed", tone: "ok", cssVar: "--truth" },
};

export const NAV = [
  { path: "/dashboard", label: "Live map" },
  { path: "/reports", label: "Reports" },
  { path: "/coaching", label: "Coaching" },
  { path: "/", hash: "how", label: "How it works" },
] as const;

export const BUS_COPY = {
  heroTitle: "Every London bus,",
  heroItalic: "a second pair of eyes.",
  heroSub:
    "SixthSense watches bus camera footage, spots close calls, predicts the next few seconds, then checks the next clip to see if it was right.",
  visionZero: "TfL's goal: no one killed on or by a London bus by 2030.",
  visionZeroUrl:
    "https://tfl.gov.uk/info-for/media/press-releases/2018/october/london-s-bus-network-to-meet-new-world-leading-bus-safety-standard",
  honest:
    "Bus positions are live from TfL open data, placed at each bus's next stop. Clips are stand-in footage from San Francisco and New York, paired to live buses for this demo.",
  poweredBy: "Powered by TfL Open Data",
  standIn: "Stand-in clip",
  noToken: "Map needs a Mapbox token",
  noTokenBody: "Add MAPBOX_TOKEN to the app's secret to see the map. Buses and reports below still update live.",
  needsLook: "Needs a look",
  needsLookNone: "No buses need a look right now.",
  routes: "Routes",
  routeSearch: "Find a route",
  follow: "Follow bus",
  following: "Following",
  showRoute: "Show route",
  openReport: "Open report",
  showOnMap: "Show on map",
  busGone: "That bus isn't on the road right now.",
  towards: "Towards",
  nextStop: "Next stop",
  timeline: ["Spotted", "Driver nudged", "Pinned on the map", "Checked the next clip", "Report filed"] as const,
};

export function etaText(s: number): string {
  if (s < 60) return "due";
  return `${Math.round(s / 60)} min`;
}

/** Pill for a paired bus in "Needs a look": Watching until checked, then the verdict. */
export function pairingPill(p: Pairing): { label: string; tone: Tone } {
  switch (p.came_true) {
    case "yes":
      return { label: "Report filed", tone: "ok" };
    case "partly":
      return { label: "Partly", tone: "mid" };
    case "no":
      return { label: "Didn't happen", tone: "hi" };
    default:
      return { label: "Watching", tone: "mid" };
  }
}
