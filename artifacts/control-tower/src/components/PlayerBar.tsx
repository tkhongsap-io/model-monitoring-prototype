/** Live control bar — docked bottom, always visible. Replaces the baked
 * scenario transport with the LIVE plane: "Observe next window" advances all
 * runners (POST /api/live/tick-all), an auto-poll toggle observes on a timer,
 * and a per-model readout shows the last observed live tick + waiting/stale hints.
 * Keyboard: Space observes the next window. */
import React, { useEffect } from "react";
import { useLive } from "@/lib/live";

export function PlayerBar() {
  const { summary, rows, auto, setAuto, tickAll, loading } = useLive();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return;
      if (e.key === " ") { e.preventDefault(); tickAll(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tickAll]);

  const asOf = summary?.as_of || {};
  const anyWaiting = rows.some((r) => r.waiting);
  const anyStale = rows.some((r) => r.stale);

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-700 bg-slate-900 px-4 py-2 text-white">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-2 text-sm">
        <button className="btnbar" onClick={() => tickAll()} title="Observe next window (Space)">⏩ Observe next window</button>
        <label className="flex items-center gap-1 text-xs font-semibold">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
          Auto-observe (5s)
        </label>
        {auto && <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" title="auto-observe running" />}

        <span className="ml-4 flex flex-wrap items-center gap-2 text-xs">
          {rows.length === 0 && <span className="text-slate-400">{loading ? "connecting…" : "no live models"}</span>}
          {rows.map((r) => {
            const tick = asOf[r.registry_id];
            return (
              <span key={r.registry_id}
                className={`rounded px-2 py-0.5 font-semibold ${r.stale ? "bg-amber-700" : "bg-slate-800"}`}
                title={r.stale ? "app offline — showing last observed window" : r.waiting ? "waiting for the app to advance" : "live"}>
                {r.registry_id.replace("AICT-", "")}: {tick == null ? "—" : `t${tick}`}
                {r.waiting && " ⏳"}{r.stale && " ⚠"}
              </span>
            );
          })}
        </span>

        <span className="ml-auto flex items-center gap-3 text-xs text-slate-300">
          {anyWaiting && <span className="text-amber-300">waiting for app ticks…</span>}
          {anyStale && <span className="text-amber-400">some models stale (app offline)</span>}
          <span className="rounded bg-[#E60012] px-2 py-0.5 font-bold">LIVE</span>
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
