/**
 * Live context — the LIVE plane. Mirrors SimProvider (lib/sim.tsx) but sourced
 * from the parallel /api/live/* endpoints that observe the three REAL models
 * (AICT-L01 churn · AICT-L02 chatbot · AICT-L03 NBA) over HTTP. Pure fetch:
 * polls GET /api/live/portfolio @4s; "Observe next window" POSTs
 * /api/live/tick-all then refetches + bumps liveVersion so detail views refetch.
 */
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export type Health = "Green" | "Amber" | "Red" | "Unknown";

export interface LiveRow {
  registry_id: string;
  use_case_name: string;
  business_unit?: string;
  platform_or_app?: string;
  status?: string;
  risk_tier?: string;
  current_health?: Health;
  overall?: Health;
  lanes?: Record<string, Health>;
  tooltips?: Record<string, { metric?: string }>;
  feedback_unknown_reason?: string | null;
  telemetry_status?: string;
  lane_kind?: "ml" | "llm";
  tick?: number | null;
  mode?: string;
  waiting?: boolean;
  stale?: boolean;
}

export interface LiveSummary {
  use_case_count: number;
  as_of: Record<string, number | null>;
  overall_counts: Record<string, number>;
  lane_counts: Record<string, Record<string, number>>;
  rows: LiveRow[];
}

interface LiveCtx {
  rows: LiveRow[];
  summary: LiveSummary | null;
  loading: boolean;
  liveVersion: number; // bump => detail views refetch
  auto: boolean;
  setAuto: (b: boolean) => void;
  tickAll: () => Promise<any>;
}

const Ctx = createContext<LiveCtx>({
  rows: [], summary: null, loading: true, liveVersion: 0, auto: false, setAuto: () => {}, tickAll: async () => {},
});

export function LiveProvider({ children }: { children: React.ReactNode }) {
  const [summary, setSummary] = useState<LiveSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [liveVersion, setLiveVersion] = useState(0);
  const [auto, setAuto] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch("/api/live/portfolio");
      if (r.ok) { setSummary(await r.json()); }
    } catch { /* backend not up yet */ }
    finally { setLoading(false); }
  }, []);

  // in-flight guard: a live tick can take 15-30s (real Claude judge + engines), so never
  // let a second tick-all overlap the first (would race the runners' cursors + hammer the backend)
  const inFlight = useRef(false);

  const tickAll = useCallback(async () => {
    if (inFlight.current) return null;
    inFlight.current = true;
    try {
      const r = await fetch("/api/live/tick-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const j = r.ok ? await r.json() : null;
      await refresh();
      setLiveVersion((v) => v + 1);
      return j;
    } catch { return null; }
    finally { inFlight.current = false; }
  }, [refresh]);

  // poll the portfolio @4s
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  // auto-observe: self-chaining loop — advance, wait for it to finish, pause, repeat.
  // (a fixed interval would stack overlapping ticks since a tick can outlast the interval)
  useEffect(() => {
    if (!auto) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const loop = async () => {
      if (cancelled) return;
      await tickAll();
      if (!cancelled) timer = setTimeout(loop, 3000);  // gap AFTER the tick completes
    };
    loop();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [auto, tickAll]);

  const rows = summary?.rows || [];

  return (
    <Ctx.Provider value={{ rows, summary, loading, liveVersion, auto, setAuto, tickAll }}>
      {children}
    </Ctx.Provider>
  );
}

export const useLive = () => useContext(Ctx);

/** Fetch an API path; refetch on mount and whenever the live version bumps. */
export function useLiveApi<T = any>(path: string): T | null {
  const { liveVersion } = useLive();
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    let alive = true;
    fetch(path).then((r) => (r.ok ? r.json() : null)).then((j) => { if (alive && j) setData(j); })
      .catch(() => {});
    return () => { alive = false; };
  }, [path, liveVersion]);
  return data;
}
