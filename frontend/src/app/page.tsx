"use client";
/** View 1 — At A Glance (PRD D.1): portfolio stat cards + full portfolio map. */
import { useRouter } from "next/navigation";
import { HEALTH_STYLE, Section, StatCard } from "@/components/ui";
import { useApi } from "@/lib/sim";

const READINESS_STYLE: Record<string, { label: string; short: string; className: string }> = {
  deep_simulated: {
    label: "Deep simulated telemetry",
    short: "Deep",
    className: "border-[#E60012] bg-red-50 text-slate-900 shadow-sm",
  },
  pilot_register_only: {
    label: "Pilot register-only",
    short: "Pilot",
    className: "border-slate-300 bg-white text-slate-800",
  },
  not_instrumented: {
    label: "Not instrumented yet",
    short: "Backlog",
    className: "border-slate-200 bg-slate-50 text-slate-500",
  },
};

export default function AtAGlance() {
  const router = useRouter();
  const s = useApi<any>("/api/summary");
  if (!s) return <Empty />;
  const sc = s.status_counts || {};
  const oc = s.overall_counts || {};
  const readiness = s.readiness_counts || {};
  const portfolio = s.portfolio_map || [];
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
          <StatCard value={s.pilot_count} label="Monitoring pilot rows" onClick={() => router.push("/pilot")} />
          <StatCard
            value={
              <span className="flex items-baseline gap-2 text-2xl">
                <span style={{ color: "#E60012" }}>{oc.Red ?? 0}</span>/
                <span style={{ color: "#B8860B" }}>{oc.Amber ?? 0}</span>/
                <span style={{ color: "#6B7280" }}>{oc.Unknown ?? 0}</span>
              </span>
            }
            label="Pilot health Red / Amber / Unknown"
            sub={`${s.open_actions} open action${s.open_actions === 1 ? "" : "s"} · ${s.critical_actions} critical · ${s.sla_breaches} escalated`}
            onClick={() => router.push("/actions")}
          />
        </div>
      </Section>
      <Section
        title="Portfolio map (130 cases)"
        right={
          <div className="hidden gap-2 text-[11px] font-semibold text-slate-500 md:flex">
            <LegendItem readiness="deep_simulated" count={readiness.deep_simulated ?? 0} />
            <LegendItem readiness="pilot_register_only" count={readiness.pilot_register_only ?? 0} />
            <LegendItem readiness="not_instrumented" count={readiness.not_instrumented ?? 0} />
          </div>
        }
      >
        <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-semibold text-slate-500 md:hidden">
            <LegendItem readiness="deep_simulated" count={readiness.deep_simulated ?? 0} />
            <LegendItem readiness="pilot_register_only" count={readiness.pilot_register_only ?? 0} />
            <LegendItem readiness="not_instrumented" count={readiness.not_instrumented ?? 0} />
          </div>
          <div className="grid gap-1.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(78px, 1fr))" }}>
            {portfolio.map((p: any) => (
              <button
                key={p.registry_id}
                title={[
                  `${p.registry_id} · ${p.use_case_name}`,
                  `readiness: ${readinessLabel(p.monitoring_readiness)}`,
                  `health: ${p.current_health || "Unknown"}`,
                  `lifecycle: ${p.status || "Unknown"}`,
                  `risk: ${p.risk_tier || "Unknown"}`,
                ].join("\n")}
                onClick={() => router.push(`/use-case/${p.registry_id}`)}
                className={`group flex min-h-8 items-center justify-between gap-1 rounded border px-2 py-1 text-left text-[11px] hover:border-[#E60012] hover:bg-red-50 ${readinessClass(p.monitoring_readiness)}`}
              >
                <span className="font-mono font-bold">{p.registry_id.replace("AICT-", "")}</span>
                <span
                  aria-label={p.current_health || "Unknown"}
                  className="h-2.5 w-2.5 shrink-0 rounded-full ring-1 ring-white"
                  style={{ background: healthColor(p.current_health) }}
                />
              </button>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
            <span><b>Readiness:</b> 2 deep telemetry · 13 pilot register-only · 115 not instrumented yet.</span>
            <span><b>Dot:</b> current health for the row; grey means Unknown.</span>
          </div>
        </div>
      </Section>
      <p className="text-[11px] text-slate-400">
        Seeded counters are a synthetic echo of the board-narrative set — one of three un-reconciled portfolio
        counts (register 131/37 · 6-Jul COE 125/35 · board 130/38), reconciliation due pre-Aug-4 [TBC]. Simulated data.
      </p>
    </div>
  );
}

function LegendItem({ readiness, count }: { readiness: string; count: number }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`h-2.5 w-2.5 rounded border ${readinessClass(readiness)}`} />
      {count} {readinessLabel(readiness)}
    </span>
  );
}

function readinessLabel(readiness?: string) {
  return READINESS_STYLE[readiness || ""]?.label || "Not instrumented yet";
}

function readinessClass(readiness?: string) {
  return READINESS_STYLE[readiness || ""]?.className || READINESS_STYLE.not_instrumented.className;
}

function healthColor(health?: string | null) {
  return (HEALTH_STYLE[health || "Unknown"] || HEALTH_STYLE.Unknown).bg;
}

function Empty() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-10 text-center text-slate-500">
      Seed data not loaded — start the backend (<code>uvicorn app.main:app --port 8000</code>) and run{" "}
      <code>scripts/demo_reset.py</code>, then reload.
    </div>
  );
}
