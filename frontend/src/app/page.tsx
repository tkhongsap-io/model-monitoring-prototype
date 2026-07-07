"use client";
/** View 1 — At A Glance (PRD D.1): portfolio stat cards + pilot health strip. */
import { useRouter } from "next/navigation";
import { HealthChip, Section, StatCard } from "@/components/ui";
import { useApi } from "@/lib/sim";

export default function AtAGlance() {
  const router = useRouter();
  const s = useApi<any>("/api/summary");
  if (!s) return <Empty />;
  const sc = s.status_counts || {};
  const oc = s.overall_counts || {};
  return (
    <div>
      <Section title="Portfolio — at a glance">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatCard value={s.use_case_count} label="Total AI use cases" onClick={() => router.push("/portfolio")} />
          <StatCard value={sc.production ?? 0} label="Production" onClick={() => router.push("/portfolio?status=production")} />
          <StatCard value={sc.in_development ?? 0} label="In development" onClick={() => router.push("/portfolio")} />
          <StatCard value={sc.requirements_not_started ?? 0} label="Requirements / not started" onClick={() => router.push("/portfolio")} />
          <StatCard value={s.high_risk_missing_approval} label="High-risk missing approval" accent="#E60012" onClick={() => router.push("/gaps")} />
          <StatCard value={s.missing_risk_assessment} label="Missing risk assessment" accent="#FFB000" onClick={() => router.push("/gaps")} />
          <StatCard value={s.pilot_count} label="Pilot assurance set" onClick={() => router.push("/pilot")} />
          <StatCard
            value={
              <span className="flex items-baseline gap-2 text-2xl">
                <span style={{ color: "#E60012" }}>{oc.Red ?? 0}</span>/
                <span style={{ color: "#B8860B" }}>{oc.Amber ?? 0}</span>/
                <span style={{ color: "#6B7280" }}>{oc.Unknown ?? 0}</span>
              </span>
            }
            label="Pilot Red / Amber / Unknown"
            sub={`${s.open_actions} open action${s.open_actions === 1 ? "" : "s"} · ${s.critical_actions} critical · ${s.sla_breaches} escalated`}
            onClick={() => router.push("/actions")}
          />
        </div>
      </Section>
      <Section title="Pilot strip (15 cases)">
        <div className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
          {(s.pilot || []).map((p: any) => (
            <button key={p.registry_id} title={`${p.registry_id} · ${p.use_case_name}`}
              onClick={() => router.push(`/use-case/${p.registry_id}`)}
              className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2 py-1 text-xs hover:border-[#E60012]">
              <span className="font-mono font-semibold">{p.registry_id.replace("AICT-", "")}</span>
              <HealthChip health={p.current_health} small />
            </button>
          ))}
        </div>
      </Section>
      <p className="text-[11px] text-slate-400">
        Seeded counters are a synthetic echo of the board-narrative set — one of three un-reconciled portfolio
        counts (register 131/37 · 6-Jul COE 125/35 · board 130/38), reconciliation due pre-Aug-4 [TBC]. Simulated data.
      </p>
    </div>
  );
}

function Empty() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-10 text-center text-slate-500">
      Seed data not loaded — start the backend (<code>uvicorn app.main:app --port 8000</code>) and run{" "}
      <code>scripts/demo_reset.py</code>, then reload.
    </div>
  );
}
