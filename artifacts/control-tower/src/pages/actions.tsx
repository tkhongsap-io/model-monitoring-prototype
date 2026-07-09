/** View 6 — Action Queue (PRD D.6): every Red becomes an owned, dated action;
 * §11 per-severity breach behaviour; nothing silently slips. */
import { useRouter } from "@/lib/nav";
import { Fragment, useState } from "react";
import { ScrollBox, Td, Th } from "@/components/ui";
import { useApi, useSim } from "@/lib/sim";

const PRI: Record<string, string> = { Critical: "P0", High: "P1", Medium: "P2", Low: "P3" };
const BANNER: Record<string, string> = {
  Critical: "Escalated to RAI Council + CDAO",
  High: "Escalated one level (owner → business owner → Council)",
  Medium: "COE chase — flagged in weekly review",
  Low: "Monthly batch review",
};

export default function Actions() {
  const router = useRouter();
  const { presenter, state } = useSim();
  const [sev, setSev] = useState(""); const [status, setStatus] = useState(""); const [overdue, setOverdue] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const data = useApi<any>(`/api/actions${sev || status ? "?" : ""}${sev ? `severity=${sev}` : ""}${sev && status ? "&" : ""}${status ? `status=${status}` : ""}`);
  let rows = data?.actions || [];
  if (overdue) rows = rows.filter((a: any) => a.escalated || a.t_minus < 0);
  const nOpen = rows.filter((a: any) => ["Open", "In progress"].includes(a.status)).length;
  const nEsc = rows.filter((a: any) => a.escalated).length;

  const close = async (a: any) => {
    await fetch(`/api/actions/${a.action_id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "Closed", evidence_link: a.evidence_link || "evidence://retrain-and-rebaseline-2026-07-28" }),
    });
  };

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h1 className="text-lg font-bold">Action Queue</h1>
        <select className="filterbox" value={sev} onChange={(e) => setSev(e.target.value)}>
          <option value="">Severity ▾</option>
          {Object.keys(PRI).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="filterbox" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Status ▾</option>
          {["Open", "In progress", "Blocked", "Closed"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label className="flex items-center gap-1 text-xs font-semibold text-slate-600">
          <input type="checkbox" checked={overdue} onChange={(e) => setOverdue(e.target.checked)} /> Overdue only
        </label>
        <span className="ml-auto text-xs text-slate-500">{nOpen} open · {nEsc} escalated</span>
      </div>
      {rows.length === 0 ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-8 text-center font-semibold text-emerald-700">
          No open actions — nothing Red this cycle.
        </div>
      ) : (
        <ScrollBox>
          <table className="w-full">
            <thead><tr><Th>Pri</Th><Th>Action</Th><Th>Use case</Th><Th>Issue</Th><Th>Recommended action</Th><Th>Owner</Th><Th>Due</Th><Th>Escalation</Th><Th>Status</Th></tr></thead>
            <tbody>
              {rows.map((a: any) => (
                <Fragment key={a.action_id}>
                  <tr key={a.action_id}
                    className={`cursor-pointer hover:bg-slate-50 ${a.escalated ? "border-l-4 border-l-[#E60012]" : ""}`}
                    onClick={() => setExpanded(expanded === a.action_id ? null : a.action_id)}>
                    <Td>
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-extrabold text-white ${a.severity === "Critical" ? "bg-[#E60012]" : a.severity === "High" ? "bg-orange-500" : a.severity === "Medium" ? "bg-amber-400 text-black" : "bg-slate-400"}`}>
                        {PRI[a.severity]}
                      </span>
                      <div className="text-[10px] text-slate-400">{a.severity}</div>
                    </Td>
                    <Td className="font-mono font-bold">{a.action_id}</Td>
                    <Td>
                      <button className="text-left hover:text-[#E60012]" onClick={(e) => { e.stopPropagation(); router.push(`/use-case/${a.registry_id}`); }}>
                        {a.use_case_name}<div className="font-mono text-[10px] text-slate-400">{a.registry_id}</div>
                      </button>
                    </Td>
                    <Td>{a.issue}</Td>
                    <Td className="max-w-[260px] truncate" title={a.recommended_action}>{a.recommended_action}</Td>
                    <Td>{a.owner}</Td>
                    <Td>
                      {a.status === "Closed" ? <span className="text-slate-400">—</span> : (
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${a.t_minus < 0 ? "bg-[#E60012] text-white" : a.t_minus <= 1 ? "bg-amber-300" : "bg-slate-100"}`}>
                          {a.due_date} {a.t_minus < 0 ? `OVERDUE +${-a.t_minus}` : `T-${a.t_minus}`}
                        </span>
                      )}
                    </Td>
                    <Td>
                      {a.escalated
                        ? <span className="rounded bg-[#E60012] px-1.5 py-0.5 text-[10px] font-extrabold text-white">AUTO-ESCALATED</span>
                        : <span className="text-xs text-slate-500">{a.escalation_path}</span>}
                    </Td>
                    <Td>
                      <span className={`text-xs font-bold ${a.status === "Closed" ? "text-emerald-600" : "text-slate-700"}`}>{a.status}</span>
                      {presenter && a.status !== "Closed" && (
                        <button className="ml-2 rounded border border-emerald-500 px-1.5 py-0.5 text-[10px] font-bold text-emerald-600 hover:bg-emerald-50"
                          onClick={(e) => { e.stopPropagation(); close(a); }}>
                          Close with evidence
                        </button>
                      )}
                    </Td>
                  </tr>
                  {expanded === a.action_id && (
                    <tr key={`${a.action_id}-x`}>
                      <Td className="bg-slate-50" />
                      <td colSpan={8} className="border-t border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                        {a.escalated && <div className="mb-1 font-bold text-[#E60012]">{BANNER[a.severity]}</div>}
                        <div className="font-semibold">History:</div>
                        {(a.history || []).map((h: any, i: number) => (
                          <div key={i}>t{h.tick} — {h.event}</div>
                        ))}
                        {a.evidence_link && <div className="mt-1">Evidence: <code>{a.evidence_link}</code></div>}
                        <div className="mt-1 text-[10px] text-slate-400">
                          Ad-hoc edits live in the session overlay and are discarded on jump/reset; the scripted t15
                          &quot;Close with evidence&quot; persists in the baked timeline.
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </ScrollBox>
      )}
      <p className="mt-2 text-[11px] text-slate-400">
        P0–P3 display the §11 severity (Critical→P0 · High→P1 · Medium→P2 · Low→P3); the dashboard-prototype&apos;s
        trigger classes are subsumed by the §10/§11 severity map. SLAs: Critical 48 h (2 ticks) · High 5 wd · Medium 15 wd · Low 30 wd.
        As of Day {state?.tick ?? 0}: 1 tick = 1 simulated working day.
      </p>
      <style>{`.filterbox { border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 8px; font-size: 12px; background: white; }`}</style>
    </div>
  );
}
