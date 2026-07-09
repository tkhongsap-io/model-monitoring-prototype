/** View 7 — Board Narrative Panel (PRD D.7): five governance claims + live proof.
 * Read-only, screenshot-ready; no board-only role. */
import { useApi, useSim } from "@/lib/sim";

export default function Board() {
  const { state } = useSim();
  const data = useApi<any>("/api/board-narrative");
  if (!data) return null;
  const stats = data.statements || [];
  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-5 rounded-lg p-5 text-white" style={{ background: "linear-gradient(120deg,#101010,#1a1a1a 60%,#E60012 140%)" }}>
        <h1 className="text-xl font-extrabold">AI Use Case Observability — Board View</h1>
        <div className="mt-1 text-xs text-white/70">
          As of Day {data.as_of_tick} · {data.date} (simulated) · <b>CPG Confidential · Simulated data</b>
        </div>
      </div>
      <div className="space-y-4">
        {stats.map((s: any, i: number) => (
          <div key={i} className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:flex-row md:items-center">
            <div className="flex-1">
              <div className="text-[10px] font-extrabold tracking-widest text-[#E60012]">CLAIM {i + 1}</div>
              <p className="mt-0.5 font-semibold text-slate-800">{s.text}</p>
            </div>
            <div className="rounded-lg bg-slate-50 px-4 py-2 text-sm md:min-w-[280px]">
              <Proof stat={s.stat} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3 md:grid-cols-6">
        {Object.entries(data.proof_stats || {}).map(([k, v]) => (
          <div key={k} className="rounded-lg border border-slate-200 bg-white p-3 text-center shadow-sm">
            <div className="text-xl font-extrabold text-slate-800">{v === null ? "—" : String(v)}</div>
            <div className="mt-1 text-[9px] font-bold uppercase tracking-wide text-slate-400">{k.replace(/_/g, " ")}</div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-center text-[11px] text-slate-400">
        Red/amber/unknown items become action queues, not hidden spreadsheet gaps. Every number above is computed
        live from the running registry at Day {state?.tick ?? 0} — simulated data, seed {state?.seed}.
      </p>
    </div>
  );
}

function Proof({ stat }: { stat: any }) {
  if (!stat) return <span className="text-slate-400">no data yet</span>;
  return (
    <div className="space-y-0.5">
      {Object.entries(stat).map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3">
          <span className="text-[11px] text-slate-500">{k.replace(/_/g, " ")}</span>
          <span className="text-right font-bold text-slate-800">
            {typeof v === "object" && v !== null
              ? Object.entries(v as any).map(([kk, vv]) => `${kk} ${vv}`).join(" · ")
              : v === null ? "—" : String(v)}
          </span>
        </div>
      ))}
    </div>
  );
}
