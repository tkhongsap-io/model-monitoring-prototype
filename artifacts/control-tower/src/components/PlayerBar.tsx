/** Scenario player bar (PRD D.9) — docked bottom, always visible.
 * Transport: play/pause · step ±1 · jump · reset · speed 1×/2×/4× · scenario picker
 * · snapshot loader. Keyboard: Space play/pause · ←/→ step · R reset. */
import React, { useEffect, useState } from "react";
import { simDay, useSim } from "@/lib/sim";

const SCENARIOS = [
  { id: "DEMO-FULL", label: "DEMO-FULL — 20-tick master" },
  { id: "S1", label: "S1 Steady state" },
  { id: "S2", label: "S2 ML drift" },
  { id: "S3", label: "S3 LLM degradation" },
  { id: "S4", label: "S4 SLA breach" },
  { id: "S5", label: "S5 Remediate & recover" },
];

export function PlayerBar() {
  const { state, control, presenter, setPresenter } = useSim();
  const [jumpTo, setJumpTo] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return;
      if (!presenter) return;
      if (e.key === " ") { e.preventDefault(); if (state?.playing) control("pause"); else control("play"); }
      else if (e.key === "ArrowRight") { e.preventDefault(); control("step"); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); control("jump", { tick: Math.max(0, (state?.tick ?? 0) - 1) }); }
      else if (e.key === "r" || e.key === "R") { control("reset"); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state, control, presenter]);

  const summary = state?.summary || {};
  const openTxt = summary.open_actions
    ? `${summary.open_actions} open action${summary.open_actions === 1 ? "" : "s"}${summary.critical_actions ? ` (${summary.critical_actions} Critical)` : ""}`
    : "no open actions";

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-700 bg-slate-900 px-4 py-2 text-white">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-2 text-sm">
        <select
          className="rounded bg-slate-800 px-2 py-1 text-xs font-semibold"
          value={state?.scenario_id || "DEMO-FULL"} disabled={!presenter}
          onChange={(e) => control("load", { scenario_id: e.target.value })}>
          {SCENARIOS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
        <button className="btnbar" disabled={!presenter} onClick={() => control("reset")} title="Reset (R)">⏮ Reset</button>
        <button className="btnbar" disabled={!presenter}
          onClick={() => (state?.playing ? control("pause") : control("play"))} title="Play/Pause (Space)">
          {state?.playing ? "⏸ Pause" : "▶ Play"}
        </button>
        <button className="btnbar" disabled={!presenter}
          onClick={() => control("jump", { tick: Math.max(0, (state?.tick ?? 0) - 1) })} title="Step back (←)">⏪ −1</button>
        <button className="btnbar" disabled={!presenter} onClick={() => control("step")} title="Step (→)">⏩ +1</button>
        <span className="flex items-center gap-1">
          <input value={jumpTo} onChange={(e) => setJumpTo(e.target.value)} placeholder="t…"
            className="w-12 rounded bg-slate-800 px-1.5 py-1 text-xs" disabled={!presenter} />
          <button className="btnbar" disabled={!presenter || jumpTo === ""}
            onClick={() => { control("jump", { tick: parseInt(jumpTo, 10) || 0 }); setJumpTo(""); }}>⏭ Jump</button>
        </span>
        <span className="flex overflow-hidden rounded border border-slate-700">
          {[1, 2, 4].map((m) => (
            <button key={m} disabled={!presenter}
              className={`px-2 py-1 text-xs font-bold ${state?.speed === m ? "bg-[#E60012]" : "bg-slate-800 hover:bg-slate-700"}`}
              onClick={() => control("speed", { multiplier: m })}>{m}×</button>
          ))}
        </span>
        {state?.snapshots && (
          <select className="rounded bg-slate-800 px-2 py-1 text-xs" value="" disabled={!presenter}
            onChange={(e) => { if (e.target.value !== "") control("jump", { tick: parseInt(e.target.value, 10) }); }}>
            <option value="">Snapshot…</option>
            {Object.entries(state.snapshots).map(([name, t]) => (
              <option key={name} value={t as number}>{name} (t{t as number})</option>
            ))}
          </select>
        )}
        <span className="ml-auto flex items-center gap-3 text-xs text-slate-300">
          <span className={`rounded px-2 py-0.5 font-bold ${state?.baked ? "bg-emerald-700" : "bg-amber-600"}`}>
            {state?.baked ? `BAKED ✓ · seed ${state?.seed}` : "NOT BAKED — run scripts/demo_reset"}
          </span>
          <span className="font-semibold text-white">{simDay(state)}</span>
          <span>{openTxt}</span>
          <select className="rounded bg-slate-800 px-2 py-1 text-xs font-semibold"
            value={presenter ? "presenter" : "viewer"}
            onChange={(e) => setPresenter(e.target.value === "presenter")}>
            <option value="presenter">Presenter</option>
            <option value="viewer">Viewer (read-only)</option>
          </select>
        </span>
      </div>
      <style>{`
        .btnbar { background: #1e293b; border-radius: 4px; padding: 4px 8px; font-size: 12px; font-weight: 600; }
        .btnbar:hover:not(:disabled) { background: #334155; }
        .btnbar:disabled { opacity: 0.4; }
      `}</style>
    </div>
  );
}
