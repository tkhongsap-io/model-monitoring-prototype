/**
 * Sim context — server-synced scenario state (PRD D.9: player state lives
 * server-side; every client shows the same simulated moment) + tick reactivity
 * (D.0: SSE via GET /api/events, poll fallback GET /api/scenario/state @2s).
 */
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export type Health = "Green" | "Amber" | "Red" | "Unknown";

export interface ScenarioState {
  scenario_id: string;
  tick: number;
  total_ticks: number;
  playing: boolean;
  speed: number;
  mode: string;
  seed: number;
  baked: boolean;
  date?: string;
  events_this_tick?: any[];
  summary?: { open_actions?: number; critical_actions?: number; sla_breaches?: number };
  snapshots?: Record<string, number>;
}

interface SimCtx {
  state: ScenarioState | null;
  version: number; // bump => views refetch
  toasts: { id: number; text: string; kind: string }[];
  presenter: boolean;
  setPresenter: (b: boolean) => void;
  control: (path: string, body?: any) => Promise<any>;
}

const Ctx = createContext<SimCtx>({
  state: null, version: 0, toasts: [], presenter: true, setPresenter: () => {}, control: async () => {},
});

let toastSeq = 1;

export function SimProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ScenarioState | null>(null);
  const [version, setVersion] = useState(0);
  const [toasts, setToasts] = useState<{ id: number; text: string; kind: string }[]>([]);
  const [presenter, setPresenter] = useState(true);
  const esRef = useRef<EventSource | null>(null);

  const pushToast = useCallback((text: string, kind = "info") => {
    const id = toastSeq++;
    setToasts((t) => [...t, { id, text, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
  }, []);

  useEffect(() => {
    let pollTimer: any = null;
    const poll = async () => {
      try {
        const r = await fetch("/api/scenario/state");
        if (r.ok) { setState(await r.json()); setVersion((v) => v + 1); }
      } catch { /* backend not up yet */ }
    };
    try {
      const es = new EventSource("/api/events");
      esRef.current = es;
      es.addEventListener("scenario_state", (e: MessageEvent) => {
        setState(JSON.parse(e.data)); setVersion((v) => v + 1);
      });
      es.addEventListener("action_opened", (e: MessageEvent) => {
        const d = JSON.parse(e.data);
        pushToast(`Action ${d.action_id} fired — ${d.severity} on ${d.registry_id} (due t${d.due_tick})`, "red");
        setVersion((v) => v + 1);
      });
      es.addEventListener("action_escalated", (e: MessageEvent) => {
        const d = JSON.parse(e.data);
        pushToast(`SLA BREACHED — ${d.action_id} auto-escalated: ${d.escalation}`, "red");
        setVersion((v) => v + 1);
      });
      es.addEventListener("action_closed", () => setVersion((v) => v + 1));
      es.addEventListener("WEEKLY_REVIEW", () => { pushToast("Weekly review — Amber persistence evaluated", "info"); });
      es.onerror = () => {
        // poll fallback @2s (D.0)
        if (!pollTimer) pollTimer = setInterval(poll, 2000);
      };
      es.onopen = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } };
    } catch {
      pollTimer = setInterval(poll, 2000);
    }
    poll();
    return () => { esRef.current?.close(); if (pollTimer) clearInterval(pollTimer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const control = useCallback(async (path: string, body?: any) => {
    const r = await fetch(`/api/scenario/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (r.ok) { setVersion((v) => v + 1); const j = await r.json(); await refreshState(); return j; }
    return null;
  }, []);

  const refreshState = async () => {
    try {
      const r = await fetch("/api/scenario/state");
      if (r.ok) setState(await r.json());
    } catch { /* ignore */ }
  };

  return (
    <Ctx.Provider value={{ state, version, toasts, presenter, setPresenter, control }}>
      {children}
    </Ctx.Provider>
  );
}

export const useSim = () => useContext(Ctx);

/** Fetch an API path; refetch when the sim version bumps. */
export function useApi<T = any>(path: string): T | null {
  const { version } = useSim();
  const [data, setData] = useState<T | null>(null);
  useEffect(() => {
    let alive = true;
    fetch(path).then((r) => (r.ok ? r.json() : null)).then((j) => { if (alive && j) setData(j); })
      .catch(() => {});
    return () => { alive = false; };
  }, [path, version]);
  return data;
}

export function simDay(state: ScenarioState | null): string {
  if (!state) return "—";
  return `Day ${state.tick}${state.total_ticks ? ` / ${state.total_ticks - 1}` : ""} · ${state.date ?? ""} (simulated)`;
}
