/** View 5 — Risk & Evidence Gaps (PRD D.5): typed, countable, actionable gaps. */
import { useRouter } from "@/lib/nav";
import { useState } from "react";
import { GreyChip } from "@/components/ui";
import { useApi } from "@/lib/sim";

const GAPS = [
  { id: "risk-unknown", name: "Risk tier unknown",
    rule: "risk_tier = Unknown AND status = production",
    action: "Assign owner + due date for risk screening",
    test: (r: any) => r.risk_tier === "Unknown" && r.status === "production",
    field: "risk_tier" },
  { id: "privacy", name: "DPO / privacy status unclear",
    rule: "privacy_status ∈ {Unknown, Required, In review}",
    action: "Escalate to DPO if personal data is likely",
    test: (r: any) => ["Unknown", "Required", "In review"].includes(r.privacy_status),
    field: "privacy_status" },
  { id: "security", name: "Security assessment incomplete",
    rule: "security_status ∈ {Not started, In review, Unknown}",
    action: "Track in shared risk register",
    test: (r: any) => ["Not started", "In review", "Unknown"].includes(r.security_status),
    field: "security_status" },
  { id: "readiness", name: "Readiness checklist missing",
    rule: "ai_readiness_status ∈ {Missing, Unknown}",
    action: "Block production sign-off until evidence exists",
    test: (r: any) => ["Missing", "Unknown"].includes(r.ai_readiness_status),
    field: "ai_readiness_status" },
  { id: "monitoring", name: "Monitoring plan absent",
    rule: "telemetry_status ∈ {Missing, Unknown}",
    action: "Mark health Unknown until cadence + metrics exist",
    test: (r: any) => ["Missing", "Unknown"].includes(r.telemetry_status),
    field: "telemetry_status" },
];

export default function Gaps() {
  const router = useRouter();
  const [open, setOpen] = useState<string | null>(null);
  const data = useApi<any>("/api/registry");
  const rows = data?.rows || [];
  return (
    <div>
      <h1 className="mb-3 text-lg font-bold">Risk &amp; Evidence Gaps</h1>
      <div className="space-y-3">
        {GAPS.map((g) => {
          const cases = rows.filter(g.test);
          const isOpen = open === g.id;
          return (
            <div key={g.id} className={`rounded-lg border bg-white p-4 shadow-sm ${cases.length === 0 ? "opacity-60" : "border-slate-200"}`}>
              <button className="flex w-full items-center gap-3 text-left" onClick={() => setOpen(isOpen ? null : g.id)}>
                <span className={`min-w-[3rem] rounded px-2 py-1 text-center text-lg font-extrabold ${cases.length ? "bg-[#E60012] text-white" : "bg-slate-100 text-slate-400"}`}>
                  {cases.length}
                </span>
                <span>
                  <span className="block font-bold">{g.name}</span>
                  <span className="block text-xs text-slate-500">Detection: <code>{g.rule}</code> · Action rule: {g.action}</span>
                </span>
                <span className="ml-auto text-slate-400">{isOpen ? "▲" : "▼"}</span>
              </button>
              {isOpen && (
                <div className="mt-3 border-t border-slate-100 pt-2">
                  {cases.length === 0 ? (
                    <div className="text-xs text-slate-400">0 — no cases (absence of gaps is information)</div>
                  ) : cases.slice(0, 20).map((r: any) => (
                    <div key={r.registry_id} className="flex items-center gap-3 border-b border-slate-50 py-1.5 text-sm">
                      <span className="font-mono text-xs">{r.registry_id}</span>
                      <button className="font-semibold hover:text-[#E60012]"
                        onClick={() => Number(r.registry_id.split("P")[1]) <= 15 && router.push(`/use-case/${r.registry_id}`)}>
                        {r.use_case_name}
                      </button>
                      <GreyChip text={`${g.field}: ${r[g.field]}`} />
                      <span className="ml-auto text-xs text-slate-500">{r.monitoring_owner}</span>
                    </div>
                  ))}
                  {cases.length > 20 && <div className="pt-1 text-[11px] text-slate-400">…and {cases.length - 20} more.</div>}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-[11px] text-slate-400">
        Standing gaps in the seeded portfolio (the seeded counter set — 4 high-risk-missing-approval, 12 missing-risk-assessment).
        Shipped scenarios do not mutate evidence fields.
      </p>
    </div>
  );
}
