import type { Pairing } from "@/lib/api/types";

// Unchecked first (still needs a decision), then came true, partly, didn't happen.
const OUTCOME_ORDER: Record<Pairing["came_true"], number> = { unknown: 0, yes: 1, partly: 2, no: 3 };

/** Attention order shared by the map markers and the "Needs a look" list: risk desc, then outcome. */
export function rankPairings(pairings: Pairing[]): Pairing[] {
  return [...pairings].sort((a, b) => b.risk - a.risk || OUTCOME_ORDER[a.came_true] - OUTCOME_ORDER[b.came_true]);
}
