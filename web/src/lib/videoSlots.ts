// At most 3 clip stills load through <video> at once, so a long list doesn't saturate the clip proxy.
const MAX_LOADING = 3;
let active = 0;
const waiting: (() => void)[] = [];

/** Resolves with a release function once a loading slot is free. */
export function acquireVideoSlot(): Promise<() => void> {
  return new Promise((resolve) => {
    const grant = () => {
      active += 1;
      let released = false;
      resolve(() => {
        if (released) return;
        released = true;
        active -= 1;
        waiting.shift()?.();
      });
    };
    if (active < MAX_LOADING) grant();
    else waiting.push(grant);
  });
}
