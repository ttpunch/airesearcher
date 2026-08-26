"use client";

import { useEffect, useState } from "react";
import { fetchTenderAnalysis, fetchTenders, type Tender, type TenderAnalysis } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; tenders: Tender[]; analysis: TenderAnalysis };

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    open: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
    closed: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
    awarded: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
    unknown: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        styles[status] ?? styles.unknown
      }`}
    >
      {status}
    </span>
  );
}

function AnalysisSummary({ analysis }: { analysis: TenderAnalysis }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
        Bid-pattern summary ({analysis.total_tenders} tender{analysis.total_tenders === 1 ? "" : "s"})
      </h2>
      <div className="flex flex-wrap gap-2">
        {Object.entries(analysis.by_status).map(([status, count]) => (
          <span key={status} className="flex items-center gap-1.5">
            <StatusBadge status={status} />
            <span className="text-xs text-zinc-500">×{count}</span>
          </span>
        ))}
      </div>
      {analysis.by_organization.length > 0 && (
        <div className="flex flex-col gap-1 border-t border-zinc-100 pt-3 text-sm dark:border-zinc-900">
          {analysis.by_organization.map((row) => (
            <div key={row.organization} className="flex justify-between text-zinc-600 dark:text-zinc-400">
              <span>{row.organization}</span>
              <span>{row.total}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function TendersPanel() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    Promise.all([fetchTenders(), fetchTenderAnalysis()])
      .then(([tenders, analysis]) => setState({ kind: "ok", tenders, analysis }))
      .catch((err) =>
        setState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" })
      );
  }, []);

  if (state.kind === "loading") {
    return <p className="text-sm text-zinc-500">Loading tenders…</p>;
  }

  if (state.kind === "error") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {state.message}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AnalysisSummary analysis={state.analysis} />

      {state.tenders.length === 0 ? (
        <p className="text-sm text-zinc-500">
          No tenders indexed yet — add one via <code>POST /api/tenders</code>.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {state.tenders.map((tender) => (
            <li
              key={tender.id}
              className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
            >
              <div className="flex items-center justify-between gap-2">
                <a
                  href={tender.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-zinc-900 underline decoration-zinc-300 hover:decoration-zinc-500 dark:text-zinc-100 dark:decoration-zinc-700"
                >
                  {tender.title}
                </a>
                <StatusBadge status={tender.status} />
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500 dark:text-zinc-500">
                <span>{tender.organization}</span>
                {tender.tender_ref && <span>Ref: {tender.tender_ref}</span>}
                {tender.closing_date && <span>Closes: {tender.closing_date}</span>}
                {tender.estimated_value && <span>Est. value: {tender.estimated_value}</span>}
              </div>
              {tender.extracted_requirements && (
                <p className="rounded-md bg-zinc-50 p-2 text-xs text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
                  Requirements extracted from the linked document — see{" "}
                  <code>GET /api/tenders/{tender.id}</code> for the structured fields.
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
