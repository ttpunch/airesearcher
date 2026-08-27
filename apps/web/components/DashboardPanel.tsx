"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchDashboardSummary, type DashboardSummary } from "@/lib/api";

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ok"; summary: DashboardSummary };

const COUNT_LABELS: [keyof DashboardSummary["counts"], string, string][] = [
  ["sources", "Sources", "/tenders"],
  ["documents", "Documents", "/ask"],
  ["chunks", "Indexed passages", "/ask"],
  ["tenders", "Tenders", "/tenders"],
  ["entities", "KG entities", "/graph"],
  ["research_reports", "Research reports", "/research"],
  ["opportunities", "Opportunities", "/opportunities"],
];

function StatTile({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    <Link href={href} className="flex flex-col gap-1.5 rounded-md border border-line bg-surface p-4.5">
      <span className="font-mono text-[28px] leading-none font-semibold text-ink">{value}</span>
      <span className="text-[11.5px] font-medium tracking-wide text-ink-faint uppercase">{label}</span>
    </Link>
  );
}

export function DashboardPanel() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    fetchDashboardSummary()
      .then((summary) => setState({ kind: "ok", summary }))
      .catch((err) =>
        setState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" })
      );
  }, []);

  if (state.kind === "loading") return <p className="text-sm text-ink-muted">Loading…</p>;
  if (state.kind === "error") {
    return <div className="rounded-md border border-err/35 bg-err/10 p-4 text-sm text-err">{state.message}</div>;
  }

  const { counts, top_opportunities } = state.summary;

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {COUNT_LABELS.map(([key, label, href]) => (
          <StatTile key={key} label={label} value={counts[key]} href={href} />
        ))}
      </div>

      <div className="flex max-w-xl flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="font-mono text-[11px] tracking-wide text-ink-faint uppercase">Top opportunities</h2>
          <Link href="/opportunities" className="text-xs text-ink-muted hover:text-ink">
            View all →
          </Link>
        </div>
        <ul className="flex flex-col gap-2">
          {top_opportunities.map((opp) => (
            <li
              key={opp.id}
              className="flex items-center justify-between gap-2 rounded-md border border-line bg-surface px-4 py-3 text-sm"
            >
              <span className="font-medium text-ink">{opp.title}</span>
              <span className="font-mono text-xs text-accent">{opp.weighted_score}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
