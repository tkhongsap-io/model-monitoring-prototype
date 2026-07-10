/** Global chrome (PRD D.9): masthead with permanent confidentiality badge,
 * 7-view nav tabs, toast stack anchored above the player bar. */
import Link from "@/lib/nav";
import { usePathname } from "@/lib/nav";
import React from "react";
import { useSim } from "@/lib/sim";

const TABS = [
  { href: "/", label: "At A Glance" },
  { href: "/heatmap", label: "Heatmap" },
];

export function Masthead() {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 text-white"
      style={{ background: "linear-gradient(120deg, #101010 0%, #1a1a1a 55%, #E60012 130%)" }}>
      <span className="rounded-full bg-white px-2.5 py-0.5 text-sm font-extrabold lowercase tracking-tight text-[#E60012]">true</span>
      <span className="text-sm font-bold">AI Use Case Observability Control Tower</span>
      <span className="rounded-full border border-white/30 bg-white/10 px-2 py-0.5 text-[10px] font-bold tracking-wider">LIVE</span>
      <span className="ml-auto rounded-full bg-[#E60012] px-2.5 py-0.5 text-[10px] font-extrabold tracking-wide">
        CPG Confidential · Live telemetry
      </span>
    </div>
  );
}

export function NavTabs() {
  const path = usePathname();
  return (
    <nav className="flex gap-1 border-b border-slate-200 bg-white px-3">
      {TABS.map((t) => {
        const active = t.href === "/" ? path === "/" : path.startsWith(t.href);
        return (
          <Link key={t.href} href={t.href}
            className={`px-3 py-2 text-sm font-semibold ${active
              ? "border-b-2 border-[#E60012] text-[#E60012]"
              : "text-slate-600 hover:text-slate-900"}`}>
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Toasts() {
  const { toasts } = useSim();
  return (
    <div className="pointer-events-none fixed bottom-24 right-4 z-50 flex w-96 flex-col gap-2">
      {toasts.map((t) => (
        <div key={t.id}
          className={`rounded-lg px-3 py-2 text-sm font-semibold text-white shadow-lg ${t.kind === "red" ? "bg-[#E60012]" : "bg-slate-800"}`}>
          {t.text}
        </div>
      ))}
    </div>
  );
}
