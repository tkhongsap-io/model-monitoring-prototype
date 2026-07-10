/** View 4 — Monitoring Lane Heatmap (PRD D.4): the signature view. */
import { useRouter } from "@/lib/nav";
import { HealthChip, Legend, ScrollBox, Td, Th, TierBadge } from "@/components/ui";
import { useLive } from "@/lib/live";

const LANES = ["Quality", "Safety & security", "Reliability", "Drift & degradation", "Feedback & action loop"];

export default function Heatmap() {
  const router = useRouter();
  const { rows, summary } = useLive();
  if (!summary) return (
    <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
      Waiting for the monitor backend — start it on <span className="font-mono">:8000</span> and observe a window.
    </div>
  );
  return (
    <div>
      <h1 className="mb-3 text-lg font-bold">Monitoring Lane Heatmap</h1>
      <ScrollBox>
        <table className="w-full">
          <thead>
            <tr>
              <Th>Use case</Th><Th>Risk</Th>
              {LANES.map((l) => <Th key={l}>{l.replace(" & action loop", "/action")}</Th>)}
              <Th>Overall</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r: any) => (
              <tr key={r.registry_id} className={`hover:bg-slate-50 ${r.stale ? "opacity-50" : ""}`}>
                <Td>
                  <button className="text-left font-semibold text-slate-800 hover:text-[#E60012]"
                    onClick={() => router.push(`/use-case/${r.registry_id}`)}>
                    {r.use_case_name}
                    <span className="ml-2 font-mono text-[10px] text-slate-400">{r.registry_id}</span>
                  </button>
                  {r.stale && <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[9px] font-semibold text-amber-700" title="App unreachable — showing the last observed window">app offline</span>}
                  {r.waiting && <span className="ml-2 rounded bg-sky-100 px-1.5 py-0.5 text-[9px] font-semibold text-sky-700" title="Monitoring is live but no window has been observed yet — observe the first window">waiting for first window</span>}
                </Td>
                <Td><TierBadge tier={r.risk_tier} /></Td>
                {LANES.map((l) => (
                  <Td key={l} className="text-center">
                    <button onClick={() => router.push(`/use-case/${r.registry_id}#${encodeURIComponent(l)}`)}>
                      <HealthChip
                        health={r.lanes?.[l] ?? "Unknown"}
                        striped={l === "Feedback & action loop" && !!r.feedback_unknown_reason}
                        title={r.feedback_unknown_reason && l === "Feedback & action loop"
                          ? r.feedback_unknown_reason
                          : `${l} — ${r.tooltips?.[l]?.metric ?? ""}`}
                      />
                    </button>
                  </Td>
                ))}
                <Td className="text-center"><HealthChip health={r.overall} /></Td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollBox>
      <Legend />
    </div>
  );
}
