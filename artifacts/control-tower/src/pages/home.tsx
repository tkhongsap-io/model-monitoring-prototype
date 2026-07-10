/** View 1 — At A Glance (LIVE): portfolio stat cards + the 3 real live models. */
import { useRouter } from "@/lib/nav";
import { HealthChip, Section, StatCard, TierBadge } from "@/components/ui";
import { useLive } from "@/lib/live";

const LANES = ["Quality", "Safety & security", "Reliability", "Drift & degradation", "Feedback & action loop"];

export default function AtAGlance() {
  const router = useRouter();
  const { summary, rows } = useLive();
  // show Empty whenever there is no data — not only during the very first load. refresh()
  // sets loading=false in finally even on a failed fetch, so gating on loading alone would
  // render a zeroed dashboard when the backend is down.
  if (!summary) return <Empty />;
  const oc = summary?.overall_counts || {};
  const count = summary?.use_case_count ?? rows.length;
  return (
    <div>
      <p className="mb-3 text-sm font-semibold text-slate-600">3 live models — real telemetry</p>
      <Section title="Portfolio — at a glance">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <StatCard value={count} label="Live AI use cases" />
          <StatCard value={oc.Red ?? 0} label="Red" accent="#E60012" />
          <StatCard value={oc.Amber ?? 0} label="Amber" accent="#B8860B" />
          <StatCard value={oc.Green ?? 0} label="Green" accent="#00A66C" />
          <StatCard value={oc.Unknown ?? 0} label="Unknown" accent="#6B7280" />
        </div>
      </Section>
      <Section title="Live models">
        <div className="flex flex-col gap-2">
          {rows.map((r) => (
            <button
              key={r.registry_id}
              onClick={() => router.push(`/use-case/${r.registry_id}`)}
              className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 text-left shadow-sm hover:border-[#E60012] hover:shadow"
            >
              <div className="min-w-[220px]">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-800">{r.use_case_name}</span>
                  {r.stale && <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[9px] font-semibold text-slate-500" title="Live app has not advanced — showing last observed window">app offline</span>}
                </div>
                <div className="font-mono text-[10px] text-slate-400">{r.registry_id} · {r.business_unit}</div>
              </div>
              <TierBadge tier={r.risk_tier} />
              <HealthChip health={r.overall} />
              <span className="ml-auto flex flex-wrap items-center gap-1">
                {LANES.map((l) => (
                  <HealthChip key={l} small health={r.lanes?.[l] ?? "Unknown"} title={`${l} — ${r.tooltips?.[l]?.metric ?? ""}`} />
                ))}
              </span>
            </button>
          ))}
        </div>
      </Section>
      <p className="text-[11px] text-slate-400">
        Live telemetry — the RAI Control Tower observes each model over HTTP and grades it through the shared health engine.
      </p>
    </div>
  );
}

function Empty() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-10 text-center text-slate-500">
      Live telemetry not available — start the backend (<code>uvicorn app.main:app --port 8000</code>) and the observed
      model apps, then reload.
    </div>
  );
}
