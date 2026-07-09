"use client";
/** Shared UI atoms — health chips per PRD D.0 (label always printed; Unknown never blank). */
import React from "react";

export const HEALTH_STYLE: Record<string, { bg: string; fg: string }> = {
  Green: { bg: "#00A66C", fg: "#fff" },
  Amber: { bg: "#FFB000", fg: "#1A1A1A" },
  Red: { bg: "#E60012", fg: "#fff" },
  Unknown: { bg: "#8A8F98", fg: "#fff" },
};

export function HealthChip({ health, small, striped, title }:
  { health?: string | null; small?: boolean; striped?: boolean; title?: string }) {
  const h = health || "Unknown";
  if (h === "—" || h === "NA") {
    return (
      <span title={title || "lane not applicable"} className={`inline-flex items-center justify-center rounded border border-[#ECEEF1] text-[#9AA0A6] ${small ? "px-1.5 py-0 text-[10px]" : "px-2 py-0.5 text-xs"}`}>—</span>
    );
  }
  const s = HEALTH_STYLE[h] || HEALTH_STYLE.Unknown;
  return (
    <span
      title={title}
      className={`inline-flex items-center justify-center rounded font-semibold ${small ? "px-1.5 py-0 text-[10px]" : "px-2 py-0.5 text-xs"}`}
      style={{
        background: striped
          ? `repeating-linear-gradient(45deg, ${s.bg}, ${s.bg} 6px, #6f747d 6px, #6f747d 12px)`
          : s.bg,
        color: s.fg,
      }}
    >
      {h}
    </span>
  );
}

export function StatCard({ value, label, sub, accent, onClick }:
  { value: React.ReactNode; label: string; sub?: React.ReactNode; accent?: string; onClick?: () => void }) {
  return (
    <button onClick={onClick} disabled={!onClick}
      className={`text-left rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${onClick ? "hover:border-[#E60012] hover:shadow" : "cursor-default"}`}>
      <div className="text-3xl font-extrabold" style={{ color: accent || "#141414" }}>{value}</div>
      <div className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
    </button>
  );
}

export function Section({ title, right, children }:
  { title: React.ReactNode; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-600">{title}</h2>
        {right}
      </div>
      {children}
    </section>
  );
}

export function ScrollBox({ children }: { children: React.ReactNode }) {
  // D.0 responsive rule: wide tables scroll inside their own container
  return <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">{children}</div>;
}

export function Th({ children }: { children?: React.ReactNode }) {
  return <th className="whitespace-nowrap bg-slate-900 px-3 py-2 text-left text-xs font-bold text-white">{children}</th>;
}

export function Td({ children, className, title }:
  { children?: React.ReactNode; className?: string; title?: string }) {
  return <td title={title} className={`whitespace-nowrap border-t border-slate-100 px-3 py-2 text-sm ${className || ""}`}>{children}</td>;
}

export function TierBadge({ tier }: { tier?: string }) {
  const color = tier === "High" ? "border-[#E60012] text-[#E60012]"
    : tier === "Medium" ? "border-amber-500 text-amber-600"
    : tier === "Low" ? "border-emerald-600 text-emerald-700"
    : "border-slate-400 text-slate-500";
  return <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${color}`}>{tier || "Unknown"}</span>;
}

export function CadenceBadge({ tier }: { tier?: string }) {
  const label = tier === "High" ? "Weekly" : tier === "Medium" ? "Monthly"
    : tier === "Low" ? "Quarterly" : "Monthly until classified";
  return <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">{label}</span>;
}

export function GreyChip({ text }: { text: string }) {
  return <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">{text}</span>;
}

export const AMBER_DOCTRINE =
  "Amber = trending toward Red — a value in the gap between the Green bar and the Red bar (trending by definition), a Red-ward trend across two weekly reviews, or a missing/stale data-or-owner gap. Sheet-3 itself defines no Amber band.";

export function Legend() {
  return (
    <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
      <b>Legend:</b> Green = Sheet-3 &quot;continue in production&quot; · Red = &quot;issue / escalate&quot; · {AMBER_DOCTRINE}{" "}
      · Unknown (grey) = missing telemetry — itself a finding · — = lane N/A.
    </p>
  );
}
