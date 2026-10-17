// The only fetch site in the web app (ESLint bans `fetch` elsewhere).
// basePath only prefixes <Link> and Next assets, so API and <video> URLs are built here.

const ROOT = process.env.NEXT_PUBLIC_API_ORIGIN ?? process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** Socket.IO endpoint: origin (dev only) + path under the basePath (/app/socket.io behind the Ingress). */
export const SOCKET_ORIGIN = process.env.NEXT_PUBLIC_API_ORIGIN;
export const SOCKET_PATH = `${process.env.NEXT_PUBLIC_API_ORIGIN ? "" : (process.env.NEXT_PUBLIC_BASE_PATH ?? "")}/socket.io`;
const API_BASE = ROOT + "/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly path: string,
  ) {
    super(`Request to ${path} failed with ${status}`);
    this.name = "ApiError";
  }
}

export function apiUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const query = params
    ? new URLSearchParams(
        Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)]),
      ).toString()
    : "";
  return API_BASE + path + (query ? `?${query}` : "");
}

export function clipUrl(source: string): string {
  // #t=0.1 makes browsers paint the first frame as a poster (needs the 206 proxy).
  return apiUrl("/clip", { source }) + "#t=0.1";
}

async function request<T>(path: string, init?: RequestInit, params?: Record<string, string | number | undefined>): Promise<T> {
  const res = await fetch(apiUrl(path, params), {
    ...init,
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
  });
  if (!res.ok) throw new ApiError(res.status, path);
  return (await res.json()) as T;
}

export function getJson<T>(path: string, params?: Record<string, string | number | undefined>, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { signal }, params);
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

/** /readyz lives outside /api and answers 503 with a body when not ready; both carry Health. */
export async function getReady<T>(signal?: AbortSignal): Promise<T> {
  const res = await fetch(ROOT + "/readyz", { signal, headers: { Accept: "application/json" } });
  if (!res.ok && res.status !== 503) throw new ApiError(res.status, "/readyz");
  return (await res.json()) as T;
}
