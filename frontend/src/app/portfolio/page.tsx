"use client";
/** View 2 — Portfolio Health (PRD D.2): five 100%-stacked slices + filtered table. */
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { HealthChip, ScrollBox, Td, Th, TierBadge } from "@/components/ui";
import { useApi } from "@/lib/sim";

const HEALTH_COLOR: Record<string, string> = { Green: "#00A66C", Amber: "#FFB000", Red: "#E60012", Unknown: "#8A8F98" };
const SLICE_COLORS = ["#0f172a", "#334155", "#64748b", "#94a3b8", "#cbd5e1", "#1e40af", "#0e7490", "#7c3aed", "#b45309", "#166534", "#9f1239", "#475569"];

function PortfolioInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [filters, setFilters] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    const st = params.get("status");
    if (st) init.status = st;
    return init;
  });
  const data = useApi<any>("/api/registry");
  const all = data?.rows || [];

  const slices: { key: string; label: string; color?: (v: string) => string }[] = [
    { key: "status", label: "Lifecycle" },
    { key: "risk_tier", label: "Risk tier" },
    { key: "platform_or_app", label: "Platform" },
    { key: "business_unit", label: "BU / domain" },
    { key: "current_health", label: "Health", color: (v) => HEALTH_COLOR[v] || "#8A8F98" },
  ];

  const filtered = useMemo(() => all.filter((r: any) =>
    Object.entries(filters).every(([k, v]) => r[k] === v)), [all, filters]);

  const agg = (key: string) => {
    const counts: Record<string, number> = {};
    for (const r of filtered) counts[r[key] ?? "Unknown"] = (counts[r[key] ?? "Unknown"] || 0) + 1;
    if (key === "current_health" || key === "risk_tier") counts["Unknown"] = counts["Unknown"] || 0;
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  };

  return (
    <div>
      <h1 className="mb-3 text-lg font-bold">Portfolio Health</h1>
      <div className="mb-4 space-y-2">
        {slices.map((s, si) => {
          const entries = agg(s.key);
          const total = entries.reduce((n, [, c]) => n + c, 0) || 1;
          return (
            <div key={s.key} className="flex items-center gap-3">
              <div className="w-24 text-xs font-bold text-slate-600">{s.label}</div>
              <div className="flex h-7 flex-1 overflow-hidden rounded">
                {entries.map(([v, c], i) => (
                  <button key={v} title={`${v}: ${c} (${Math.round((100 * c) / total)}%)`}
                    onClick={() => setFilters((f) => ({ ...f, [s.key]: v }))}
                    className="flex items-center justify-center overflow-hidden whitespace-nowrap text-[10px] font-bold text-white hover:opacity-80"
                    style={{ width: `${Math.max((100 * c) / total, 3)}%`,
                             background: s.color ? s.color(v) : SLICE_COLORS[(si * 3 + i) % SLICE_COLORS.length] }}>
                    {c > 0 && `${v} ${c}`}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mb-3 flex items-center gap-2">
        <span className="text-xs font-semibold text-slate-500">Active filters:</span>
        {Object.entries(filters).length === 0 && <span className="text-xs text-slate-400">none</span>}
        {Object.entries(filters).map(([k, v]) => (
          <button key={k} className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-semibold text-white"
            onClick={() => setFilters((f) => { const g = { ...f }; delete g[k]; return g; })}>
            {v} ×
          </button>
        ))}
        {Object.entries(filters).length > 0 && (
          <button className="text-[11px] font-semibold text-[#E60012]" onClick={() => setFilters({})}>Clear all</button>
        )}
      </div>
      {filtered.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
          No use cases match — clear a filter.
        </div>
      ) : (
        <ScrollBox>
          <table className="w-full">
            <thead><tr><Th>ID</Th><Th>Use case</Th><Th>BU</Th><Th>Platform</Th><Th>Lifecycle</Th><Th>Risk</Th><Th>Health</Th></tr></thead>
            <tbody>
              {filtered.slice(0, 60).map((r: any) => (
                <tr key={r.registry_id} className="cursor-pointer hover:bg-slate-50"
                  onClick={() => Number(r.registry_id.split("P")[1]) <= 15 && router.push(`/use-case/${r.registry_id}`)}>
                  <Td className="font-mono text-xs">{r.registry_id}</Td>
                  <Td className="font-semibold">{r.use_case_name}</Td>
                  <Td>{r.business_unit}</Td>
                  <Td className="max-w-[180px] truncate">{r.platform_or_app}</Td>
                  <Td>{r.status}</Td>
                  <Td><TierBadge tier={r.risk_tier} /></Td>
                  <Td><HealthChip health={r.current_health} /></Td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollBox>
      )}
      {filtered.length > 60 && <p className="mt-1 text-[11px] text-slate-400">Showing 60 of {filtered.length} rows.</p>}
    </div>
  );
}

export default function Portfolio() {
  return <Suspense><PortfolioInner /></Suspense>;
}
