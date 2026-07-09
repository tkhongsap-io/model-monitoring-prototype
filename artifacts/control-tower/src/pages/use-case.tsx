/** Use-case drill-down (PRD D.8): every signal vs its band, the real engine
 * artifacts behind each grade, and the action history. */
import { useParams, useRouter } from "@/lib/nav";
import { useState } from "react";
import {
  CartesianGrid, Legend as RLegend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { CadenceBadge, GreyChip, HealthChip, ScrollBox, Td, Th, TierBadge } from "@/components/ui";
import { useApi, useSim } from "@/lib/sim";

export default function UseCase() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { state } = useSim();
  const uc = useApi<any>(`/api/use-cases/${id}`);
  const isML = id === "AICT-P02";
  const [tab, setTab] = useState(0);
  if (!uc) return <div className="p-8 text-slate-400">Loading…</div>;
  const tabs = isML
    ? ["Drift (Evidently)", "Performance (NannyML)", "Explainability (LIME / SHAP)"]
    : ["Judge scores", "Traces", "Corpus & eval set"];
  const deep = (uc.signals || []).length > 0;

  return (
    <div>
      <button className="mb-2 text-xs font-semibold text-slate-400 hover:text-[#E60012]" onClick={() => router.push("/heatmap")}>
        Heatmap › {uc.use_case_name}
      </button>
      {/* header */}
      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-lg font-extrabold">{uc.use_case_name}</h1>
          <span className="font-mono text-xs text-slate-400">{uc.registry_id} · source: {uc.source_record_id}</span>
          <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-white">{uc.status}</span>
          <TierBadge tier={uc.risk_tier} />
          <HealthChip health={uc.current_health} />
          <GreyChip text={`telemetry: ${uc.telemetry_status}${uc.telemetry_status === "Live" ? " (simulated)" : ""}`} />
          <CadenceBadge tier={uc.risk_tier} />
        </div>
        <div className="mt-2 grid gap-x-6 gap-y-0.5 text-xs text-slate-600 md:grid-cols-2">
          <div><b>Owners (roles):</b> business — {uc.business_owner} · technical — {uc.technical_owner} · monitoring — {uc.monitoring_owner}</div>
          <div><b>System owner:</b> {uc.system_owner}</div>
          <div><b>Platform:</b> {uc.platform_or_app} · <b>Model:</b> {uc.model_or_route}</div>
          <div><b>Data:</b> <span title={uc.data_sources}>{String(uc.data_sources).slice(0, 60)}…</span> · reviewed {uc.last_reviewed} · next {uc.next_review}</div>
        </div>
      </div>

      {/* signals */}
      <ScrollBox>
        <table className="w-full">
          <thead><tr><Th>Signal</Th><Th>Lane</Th><Th>Value</Th><Th>Band (Green / Red)</Th><Th>Health</Th><Th>Trend</Th></tr></thead>
          <tbody>
            {(uc.signals || []).map((s: any) => (
              <tr key={s.key} id={encodeURIComponent(s.lane)}>
                <Td className="font-semibold">{s.label}
                  {s.provenance === "Sheet-3 (inherited)" && <span className="ml-1 rounded bg-slate-800 px-1 py-0.5 text-[8px] font-bold text-white">SHEET-3</span>}
                </Td>
                <Td className="text-xs text-slate-500">{s.lane}</Td>
                <Td className="font-mono">{fmt(s.value, s)}{s.pending_reason && <span className="ml-1 text-[10px] italic text-slate-400">({s.pending_reason})</span>}</Td>
                <Td className="text-xs text-slate-500">{band(s)}</Td>
                <Td><HealthChip health={s.pending_reason ? "Unknown" : s.health} striped={!!s.pending_reason} title={s.pending_reason || undefined} /></Td>
                <Td><Spark history={s.history} spec={s} /></Td>
              </tr>
            ))}
            {!deep && (
              <tr><td colSpan={6} className="p-4 text-center text-sm text-slate-400">
                Shallow registry row — no tick-simulated signals. Evidence note: {uc.evidence_note || "—"}
              </td></tr>
            )}
          </tbody>
        </table>
      </ScrollBox>

      {/* tabs */}
      {deep && (
        <div className="mt-5">
          <div className="flex gap-1 border-b border-slate-200">
            {tabs.map((t, i) => (
              <button key={t} onClick={() => setTab(i)}
                className={`px-3 py-2 text-sm font-semibold ${tab === i ? "border-b-2 border-[#E60012] text-[#E60012]" : "text-slate-500"}`}>
                {t}
              </button>
            ))}
          </div>
          <div className="mt-3">
            {isML ? <MLTabs uc={uc} tab={tab} day={state?.tick ?? 0} /> : <LLMTabs uc={uc} tab={tab} />}
          </div>
        </div>
      )}

      {/* action history */}
      <div className="mt-6">
        <h2 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-600">Action history</h2>
        {(uc.actions || []).length === 0 ? (
          <div className="text-sm text-slate-400">No actions for this use case at the current tick.</div>
        ) : (uc.actions || []).map((a: any) => (
          <div key={a.action_id} className="mb-1 flex items-center gap-2 text-sm">
            <span className="font-mono font-bold">{a.action_id}</span>
            <span className="text-xs text-slate-500">
              {(a.history || []).map((h: any) => `t${h.tick} ${h.event}`).join(" → ")}
            </span>
            <button className="text-xs font-semibold text-[#E60012]" onClick={() => router.push("/actions")}>View queue →</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function fmt(v: any, s: any) {
  if (v === null || v === undefined) return "—";
  if (s.unit === "fraction" || s.key === "pii_exposure_rate") return `${(v * 100).toFixed(1)}%`;
  if (s.key === "data_drift_share") return v.toFixed(3);
  if (s.unit === "seconds") return `${v.toFixed(1)}s`;
  return v.toFixed(3);
}

function band(s: any) {
  const g = s.direction === "lower_is_better" ? `≤ ${disp(s.green_bar, s)}` : `≥ ${disp(s.green_bar, s)}`;
  const r = s.direction === "lower_is_better" ? `≥ ${disp(s.red_bar, s)}` : `< ${disp(s.red_bar, s)}`;
  return `Green ${g} · Red ${r}`;
}
function disp(v: number, s: any) {
  if (s.unit === "fraction") return `${(v * 100).toFixed(0)}%`;
  if (s.unit === "seconds") return `${v}s`;
  return String(v);
}

function Spark({ history, spec }: { history: any[]; spec: any }) {
  const pts = (history || []).filter((h) => h.value !== null);
  if (pts.length < 2) return <span className="text-slate-300">—</span>;
  const vals = pts.map((p) => p.value);
  const min = Math.min(...vals, spec.red_bar ?? Infinity) * 0.98;
  const max = Math.max(...vals, spec.red_bar ?? -Infinity) * 1.02;
  const W = 90, H = 24;
  const x = (i: number) => (i / (pts.length - 1)) * W;
  const y = (v: number) => H - ((v - min) / (max - min || 1)) * H;
  const color = { Green: "#00A66C", Amber: "#FFB000", Red: "#E60012", Unknown: "#8A8F98" }[pts[pts.length - 1].health as string] || "#64748b";
  return (
    <svg width={W} height={H} className="overflow-visible">
      {spec.red_bar != null && (
        <line x1={0} x2={W} y1={y(spec.red_bar)} y2={y(spec.red_bar)} stroke="#E60012" strokeDasharray="3 2" strokeWidth={0.8} />
      )}
      <polyline fill="none" stroke={color} strokeWidth={1.6}
        points={pts.map((p, i) => `${x(i)},${y(p.value)}`).join(" ")} />
    </svg>
  );
}

function ArtifactFrame({ id, height = 620 }: { id?: string; height?: number }) {
  if (!id) return <div className="rounded border border-slate-200 bg-slate-50 p-6 text-sm text-slate-400">Artifact not available for this tick.</div>;
  return <iframe src={`/api/artifacts/${id}`} className="w-full rounded border border-slate-200 bg-white" style={{ height }} />;
}

function MLTabs({ uc, tab, day }: { uc: any; tab: number; day: number }) {
  const est = uc.signals?.find((s: any) => s.key === "estimated_roc_auc");
  const real = uc.signals?.find((s: any) => s.key === "realized_roc_auc");
  const chart = (est?.history || []).map((h: any) => ({
    tick: h.tick, estimated: h.value,
    realized: (real?.history || []).find((r: any) => r.tick === h.tick)?.value ?? null,
  }));
  if (tab === 0) return (
    <div>
      <p className="mb-2 text-sm"><b>Drifted features ({(uc.drifted_features || []).length}):</b>{" "}
        {(uc.drifted_features || []).join(", ") || "none reported"}</p>
      <ArtifactFrame id={uc.artifacts?.evidently_html} />
      <p className="mt-1 text-[11px] text-slate-400">Full Evidently report for the current tick · refreshed Day {day}</p>
    </div>
  );
  if (tab === 1) return (
    <div>
      <div className="h-72 w-full rounded border border-slate-200 bg-white p-2">
        <ResponsiveContainer>
          <LineChart data={chart}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="tick" fontSize={11} label={{ value: "tick (simulated day)", position: "insideBottom", offset: -2, fontSize: 10 }} />
            <YAxis domain={[0.65, 0.95]} fontSize={11} />
            <Tooltip />
            <RLegend />
            <ReferenceLine y={0.72} stroke="#E60012" strokeDasharray="4 3" label={{ value: "Red bar 0.72", fontSize: 10, fill: "#E60012" }} />
            <ReferenceLine y={0.80} stroke="#00A66C" strokeDasharray="4 3" label={{ value: "Green bar 0.80", fontSize: 10, fill: "#00A66C" }} />
            {uc.reference_auc && <ReferenceLine y={uc.reference_auc} stroke="#94a3b8" strokeDasharray="2 4" label={{ value: `reference ${uc.reference_auc}`, fontSize: 10, fill: "#94a3b8" }} />}
            <Line type="monotone" dataKey="estimated" stroke="#0f172a" strokeWidth={2} dot={false} name="Estimated (NannyML, label-free)" />
            <Line type="monotone" dataKey="realized" stroke="#E60012" strokeWidth={2} strokeDasharray="6 3" dot={{ r: 2 }} name="Realized (labels, 3-tick lag)" connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-[11px] text-slate-500">
        NannyML estimates production performance <b>before</b> ground-truth labels arrive — the early warning the
        Drift/Quality lanes rely on. Under covariate shift the estimate is <b>early but conservative</b>: it sags
        label-free while the realized line (3-tick label lag) confirms the damage is worse. Model v{uc.model_version}.
      </p>
    </div>
  );
  return (
    <div>
      {uc.lime_instance?.index !== undefined && (
        <p className="mb-2 text-sm">LIME explanation for the highest-risk customer (row {uc.lime_instance.index}, churn probability {(uc.lime_instance.churn_probability * 100).toFixed(0)}%).</p>
      )}
      <div className="grid gap-3 lg:grid-cols-2">
        <div><ArtifactFrame id={uc.artifacts?.lime_html} height={420} /></div>
        <div>
          {uc.artifacts?.shap_png
            // eslint-disable-next-line @next/next/no-img-element
            ? <img src={`/api/artifacts/${uc.artifacts.shap_png}`} alt="SHAP global importance" className="w-full rounded border border-slate-200 bg-white" />
            : <div className="rounded border border-slate-200 bg-slate-50 p-6 text-sm text-slate-400">SHAP not available.</div>}
          <p className="mt-1 text-[11px] text-slate-500">SHAP global feature importance (model v{uc.model_version}).</p>
        </div>
      </div>
      <p className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-800">
        LIME explanations are local and can be unstable (fidelity-vs-simplicity trade-off). SHAP is the more
        consistent, game-theoretic counterpart — and what the enterprise path (Azure ML Responsible AI dashboard) uses.
      </p>
    </div>
  );
}

function LLMTabs({ uc, tab }: { uc: any; tab: number }) {
  if (tab === 0) return (
    <div>
      <div className="mb-2 rounded border border-slate-300 bg-slate-100 p-2 text-[11px] font-bold text-slate-600">
        SIMULATED JUDGE — deterministic seeded simulation (count-based hallucination injection + seeded score draws).
        Offline/simulated only; no live-LLM mode ships in demo scope.
      </div>
      <ScrollBox>
        <table className="w-full">
          <thead><tr><Th>Question</Th><Th>Answer (≤80 chars)</Th><Th>Ground.</Th><Th>Relev.</Th><Th>Halluc.</Th><Th>PII</Th><Th>Latency</Th></tr></thead>
          <tbody>
            {(uc.judge_sample || []).map((r: any, i: number) => (
              <tr key={i} className={r.hallucination ? "bg-red-50" : ""}>
                <Td className="max-w-[260px] truncate" title={r.question}>{r.question}</Td>
                <Td className="max-w-[260px] truncate text-xs" title={r.answer}>{r.answer}</Td>
                <Td className="font-mono">{r.groundedness}</Td>
                <Td className="font-mono">{r.relevance}</Td>
                <Td>{r.hallucination ? <span className="font-bold text-[#E60012]">YES</span> : "no"}</Td>
                <Td>{r.pii ? "YES" : "no"}</Td>
                <Td className="font-mono">{r.latency_s}s</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollBox>
    </div>
  );
  if (tab === 1) return (
    <div>
      <p className="mb-2 text-[11px] text-slate-500">
        Traces read from the SQLite-backed trace store (Langfuse stub — same interface as Langfuse SDK v2) via the API.
      </p>
      <ScrollBox>
        <table className="w-full">
          <thead><tr><Th>Trace</Th><Th>Input</Th><Th>Output</Th><Th>Scores</Th><Th>Latency</Th></tr></thead>
          <tbody>
            {(uc.artifacts?.traces || []).slice(0, 25).map((t: any) => (
              <tr key={t.trace_id}>
                <Td className="font-mono text-[10px]">{t.trace_id.slice(0, 8)}…</Td>
                <Td className="max-w-[220px] truncate" title={t.input}>{t.input}</Td>
                <Td className="max-w-[260px] truncate text-xs" title={t.output}>{t.output}</Td>
                <Td className="text-xs">{Object.entries(t.scores || {}).map(([k, v]: any) => `${k}=${(+v).toFixed(2)}`).join(" · ")}</Td>
                <Td className="font-mono text-xs">{t.metadata?.latency_s}s</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollBox>
    </div>
  );
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <h3 className="mb-1 text-sm font-bold">Corpus — 6 policy topics</h3>
        {Object.entries(uc.corpus?.topics || {}).map(([k, v]: any) => (
          <div key={k} className="mb-2 rounded border border-slate-200 bg-white p-2 text-xs">
            <b className="font-mono">{k}</b>: {v}
          </div>
        ))}
      </div>
      <div>
        <h3 className="mb-1 text-sm font-bold">Eval set — 10 questions (3 deliberately unanswerable)</h3>
        {(uc.corpus?.qa || []).map((q: any, i: number) => (
          <div key={i} className={`mb-1 rounded border p-2 text-xs ${q.answerable ? "border-slate-200 bg-white" : "border-amber-300 bg-amber-50"}`}>
            <b>{q.question}</b>
            <div className="text-slate-500">{q.reference} {!q.answerable && <span className="font-bold text-amber-700">· UNANSWERABLE (refusal test)</span>}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
