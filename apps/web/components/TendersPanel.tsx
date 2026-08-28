"use client";

import { useEffect, useState } from "react";
import { fetchTenderAnalysis, fetchTenders, type Tender, type TenderAnalysis } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; tenders: Tender[]; analysis: TenderAnalysis };

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    open: "bg-info/14 text-info border-info/35",
    closed: "bg-surface-2 text-ink-muted border-line",
    awarded: "bg-ok/14 text-ok border-ok/35",
    unknown: "bg-warn/14 text-warn border-warn/35",
  };
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[10.5px] font-medium tracking-wide uppercase ${
        styles[status] ?? styles.unknown
      }`}
    >
      {status}
    </span>
  );
}

function AnalysisSummary({ analysis }: { analysis: TenderAnalysis }) {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-line bg-surface p-5">
      <h2 className="font-mono text-[11px] tracking-wide text-ink-faint uppercase">
        Bid-pattern summary ({analysis.total_tenders} tender{analysis.total_tenders === 1 ? "" : "s"})
      </h2>
      <div className="flex flex-wrap gap-2">
        {Object.entries(analysis.by_status).map(([status, count]) => (
          <span key={status} className="flex items-center gap-1.5">
            <StatusBadge status={status} />
            <span className="text-xs text-ink-faint">×{count}</span>
          </span>
        ))}
      </div>
      {analysis.by_organization.length > 0 && (
        <div className="flex flex-col gap-1 border-t border-line pt-3 text-sm">
          {analysis.by_organization.map((row) => (
            <div key={row.organization} className="flex justify-between text-ink-muted">
              <span>{row.organization}</span>
              <span className="font-mono">{row.total}</span>
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
    return <p className="text-sm text-ink-muted">Loading tenders…</p>;
  }

  if (state.kind === "error") {
    return <div className="rounded-md border border-err/35 bg-err/10 p-4 text-sm text-err">{state.message}</div>;
  }

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <AnalysisSummary analysis={state.analysis} />

      {state.tenders.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No tenders indexed yet — add one via <code className="font-mono text-ink-faint">POST /api/tenders</code>.
        </p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {state.tenders.map((tender) => (
            <li key={tender.id} className="flex flex-col gap-2 rounded-md border border-line bg-surface p-4">
              <div className="flex items-center justify-between gap-2">
                <a
                  href={tender.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-ink underline decoration-line-strong hover:decoration-accent"
                >
                  {tender.title}
                </a>
                <StatusBadge status={tender.status} />
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-faint">
                <span>{tender.organization}</span>
                {tender.tender_ref && <span className="font-mono text-ink-muted">Ref: {tender.tender_ref}</span>}
                {tender.closing_date && <span>Closes: {tender.closing_date}</span>}
                {tender.estimated_value && <span>Est. value: {tender.estimated_value}</span>}
              </div>
              {tender.extracted_requirements && (
                <p className="rounded bg-inset p-2 font-mono text-[11.5px] text-ink-faint">
                  Requirements extracted from the linked document — see GET /api/tenders/{tender.id}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
