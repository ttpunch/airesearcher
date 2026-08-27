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
    <Link
      href={href}
      className="flex flex-col gap-1 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-zinc-700"
    >
      <span className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">{value}</span>
      <span className="text-xs text-zinc-500 dark:text-zinc-500">{label}</span>
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

  if (state.kind === "loading") return <p className="text-sm text-zinc-500">Loading…</p>;
  if (state.kind === "error") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {state.message}
      </div>
    );
  }

  const { counts, top_opportunities } = state.summary;

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {COUNT_LABELS.map(([key, label, href]) => (
          <StatTile key={key} label={label} value={counts[key]} href={href} />
        ))}
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
            Top opportunities
          </h2>
          <Link href="/opportunities" className="text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300">
            View all →
          </Link>
        </div>
        <ul className="flex flex-col gap-2">
          {top_opportunities.map((opp) => (
            <li
              key={opp.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-zinc-200 bg-white p-3 text-sm shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
            >
              <span className="text-zinc-900 dark:text-zinc-100">{opp.title}</span>
              <span className="text-xs text-zinc-500">score {opp.weighted_score}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
