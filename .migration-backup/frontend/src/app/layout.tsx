import type { Metadata } from "next";
import "./globals.css";
import { SimProvider } from "@/lib/sim";
import { Masthead, NavTabs, Toasts } from "@/components/Chrome";
import { PlayerBar } from "@/components/PlayerBar";

export const metadata: Metadata = {
  title: "AI Use Case Observability Control Tower — Simulation Demo",
  description:
    "CPG Confidential · Simulated data. Simulation-first demo of the RAI operating model's monitoring loop (LLM + classical ML).",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <SimProvider>
          <Masthead />
          <NavTabs />
          <main className="mx-auto max-w-[1400px] px-4 pb-32 pt-5">{children}</main>
          <Toasts />
          <PlayerBar />
        </SimProvider>
      </body>
    </html>
  );
}
