/** View 3 — Pilot Health Table (PRD D.3): the working table for the 15-row pilot set. */
import { useRouter } from "@/lib/nav";
import { useState } from "react";
import { CadenceBadge, GreyChip, HealthChip, ScrollBox, Td, Th, TierBadge } from "@/components/ui";
import { useApi, useSim } from "@/lib/sim";

const OK: Record<string, string[]> = {
  privacy_status: ["Approved", "Not required"], security_status: ["Approved"],
  rai_status: ["Complete"], ai_readiness_status: ["Complete"], telemetry_status: ["Live", "Manual"],
};
const LABEL: Record<string, string> = {
  privacy_status: "Privacy", security_status: "Security", rai_status: "RAI",
  ai_readiness_status: "Readiness", telemetry_status: "Telemetry",
};
const SEV = { Red: 0, Amber: 1, Unknown: 2, Green: 3 } as Record<string, number>;

export default function Pilot() {
  const router = useRouter();
  const { state } = useSim();
  const [healthF, setHealthF] = useState(""); const [riskF, setRiskF] = useState("");
  const data = useApi<any>("/api/registry?group=pilot");
  let rows = data?.rows || [];
  if (healthF) rows = rows.filter((r: any) => r.current_health === healthF);
  if (riskF) rows = rows.filter((r: any) => r.risk_tier === riskF);
  rows = [...rows].sort((a: any, b: any) => (SEV[a.current_health] ?? 2) - (SEV[b.current_health] ?? 2));
  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <h1 className="text-lg font-bold">Pilot Health Table</h1>
        <select className="rounded border border-slate-200 px-2 py-1 text-xs" value={healthF} onChange={(e) => setHealthF(e.target.value)}>
          <option value="">Health ▾</option>{["Red", "Amber", "Unknown", "Green"].map((h) => <option key={h}>{h}</option>)}
        </select>
        <select className="rounded border border-slate-200 px-2 py-1 text-xs" value={riskF} onChange={(e) => setRiskF(e.target.value)}>
          <option value="">Risk ▾</option>{["High", "Medium", "Low", "Unknown"].map((h) => <option key={h}>{h}</option>)}
        </select>
      </div>
      <ScrollBox>
        <table className="w-full">
          <thead><tr><Th>ID</Th><Th>Use case</Th><Th>Lifecycle</Th><Th>Risk</Th><Th>Health</Th><Th>Missing evidence</Th><Th>Next action</Th><Th>Owner</Th><Th>Due</Th></tr></thead>
          <tbody>
            {rows.map((r: any) => {
              const missing = Object.keys(OK).filter((k) => !OK[k].includes(r[k]));
              const a = r.next_action;
              const tMinus = a ? a.due_tick - (state?.tick ?? 0) : null;
              return (
                <tr key={r.registry_id} className="cursor-pointer hover:bg-slate-50" onClick={() => router.push(`/use-case/${r.registry_id}`)}>
                  <Td className="font-mono font-bold text-[#E60012]">{r.registry_id}</Td>
                  <Td><div className="font-semibold">{r.use_case_name}</div><div className="text-[10px] text-slate-400">{r.use_case_group}</div></Td>
                  <Td>{r.status}</Td>
                  <Td><TierBadge tier={r.risk_tier} /> <CadenceBadge tier={r.risk_tier} /></Td>
                  <Td><HealthChip health={r.current_health} /></Td>
                  <Td title={missing.map((k) => `${LABEL[k]}: ${r[k]}`).join(" · ")}>
                    {missing.length === 0 ? <span className="text-slate-300">—</span>
                      : missing.map((k) => (
                        r[k] === "Unknown" ? <GreyChip key={k} text={LABEL[k]} />
                          : <span key={k} className="mr-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">{LABEL[k]}</span>
                      ))}
                  </Td>
                  <Td className="max-w-[240px] truncate" title={a?.recommended_action}>
                    {a ? a.recommended_action : <span className="text-slate-300">—</span>}
                  </Td>
                  <Td>{r.monitoring_owner === "Unknown" ? <GreyChip text="Unknown" /> : r.monitoring_owner}</Td>
                  <Td>
                    {a ? (
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${tMinus! < 0 ? "bg-[#E60012] text-white" : "bg-slate-100"}`}>
                        {a.due_date} {tMinus! < 0 ? `OVERDUE +${-tMinus!}` : `T-${tMinus}`}
                      </span>
                    ) : <span className="text-slate-300">—</span>}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ScrollBox>
      <p className="mt-2 text-[11px] text-slate-400">— in Next action/Due = nothing pending (distinct from Unknown). Sorted by health severity.</p>
    </div>
  );
}
