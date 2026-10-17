"use client";

// Per-viewer sign-off, kept in this browser only (no backend field for review state yet).
import { useCallback, useSyncExternalStore } from "react";

const KEY = "sixthsense.signedOff";
const EVENT = "sixthsense:signoff";
const EMPTY = "[]";
// Fallback when storage is blocked: sign-off lasts until the tab closes.
let memory = EMPTY;

function read(): string {
  try {
    return window.localStorage.getItem(KEY) ?? EMPTY;
  } catch {
    return memory;
  }
}

function subscribe(cb: () => void) {
  window.addEventListener("storage", cb);
  window.addEventListener(EVENT, cb);
  return () => {
    window.removeEventListener("storage", cb);
    window.removeEventListener(EVENT, cb);
  };
}

function parse(raw: string): string[] {
  try {
    const v: unknown = JSON.parse(raw);
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

/** Ids this viewer signed off. Snapshot is the raw string so React can compare it cheaply. */
export function useSignedOff(): Set<string> {
  const raw = useSyncExternalStore(subscribe, read, () => EMPTY);
  return new Set(parse(raw));
}

export function useSignOff(id: string) {
  const ids = useSignedOff();
  const set = useCallback(
    (on: boolean) => {
      const next = new Set(parse(read()));
      if (on) next.add(id);
      else next.delete(id);
      const value = JSON.stringify([...next]);
      try {
        window.localStorage.setItem(KEY, value);
      } catch {
        memory = value;
      }
      window.dispatchEvent(new Event(EVENT));
    },
    [id],
  );
  return { signedOff: ids.has(id), setSignedOff: set };
}
