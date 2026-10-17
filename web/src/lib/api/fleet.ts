"use client";

// Live fleet: Socket.IO push, REST polling fallback. Socket code lives here only (with fetch in client.ts).
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import { SOCKET_ORIGIN, SOCKET_PATH } from "./client";
import { queryKeys, vehiclesOptions } from "./queries";
import type { FleetSnapshot } from "./types";

const POLL_MS = 30_000;

export type FleetLink = "connecting" | "live" | "polling";

export function useFleet() {
  const queryClient = useQueryClient();
  const [link, setLink] = useState<FleetLink>("connecting");

  useEffect(() => {
    const opts = { path: SOCKET_PATH, reconnectionAttempts: 5 };
    const socket = SOCKET_ORIGIN ? io(SOCKET_ORIGIN, opts) : io(opts);
    socket.on("connect", () => setLink("live"));
    socket.on("vehicles", (snap: FleetSnapshot) => queryClient.setQueryData(queryKeys.vehicles, snap));
    socket.on("connect_error", () => setLink("polling"));
    socket.on("disconnect", () => setLink("polling"));
    return () => {
      socket.close();
    };
  }, [queryClient]);

  // REST seeds the map immediately and keeps it fresh whenever the socket is down.
  const snapshot = useQuery({ ...vehiclesOptions(), refetchInterval: link === "live" ? false : POLL_MS });
  return { snapshot, link };
}
