"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  createResearchReport,
  fetchResearchReports,
  type Reference,
  type ResearchReport,
} from "@/lib/api";
import { IconCheck } from "@/components/icons";

type ListState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; reports: ResearchReport[] };

type SubmitState = { kind: "idle" } | { kind: "loading" } | { kind: "error"; message: string };

function StatusBadge({ status }: { status: string }) {
  if (status === "completed") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded border border-ok/35 bg-ok/14 px-2.5 py-1 font-mono text-[10.5px] font-medium tracking-wide text-ok uppercase">
        <IconCheck className="h-[11px] w-[11px]" />
        Completed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-warn/35 bg-warn/14 px-2.5 py-1 font-mono text-[10.5px] font-medium tracking-wide text-warn uppercase">
      <span className="h-2 w-2 rounded-full bg-warn" />
      No evidence found
    </span>
  );
}

function ReferenceBadge({ refType }: { refType: string }) {
  const labels: Record<string, string> = { chunk: "document", tender: "tender", entity: "entity" };
  return (
    <span className="inline-flex items-center rounded bg-surface-2 px-2 py-0.5 font-mono text-[9.5px] font-medium tracking-wide text-accent uppercase">
      {labels[refType] ?? refType}
    </span>
  );
}

function ReportCard({ report }: { report: ResearchReport }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <li className="flex flex-col gap-3 rounded-md border border-line bg-surface p-5">
      <button type="button" onClick={() => setExpanded((v) => !v)} className="flex items-center justify-between gap-3 text-left">
        <span className="font-display font-semibold text-ink">{report.topic}</span>
        <StatusBadge status={report.status} />
      </button>
      {expanded && (
        <div className="flex flex-col gap-3 border-t border-line pt-3">
          <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink-muted">{report.summary}</p>
          {report.references.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {report.references.map((ref: Reference) => (
                <li
                  key={`${ref.ref_type}-${ref.ref_id}`}
                  className="flex items-center gap-1.5 rounded border border-line bg-surface-2 px-2.5 py-1.5 text-[11.5px]"
                >
                  <ReferenceBadge refType={ref.ref_type} />
                  {ref.url ? (
                    <a href={ref.url} target="_blank" rel="noopener noreferrer" className="font-medium text-ink">
                      {ref.label}
                    </a>
                  ) : (
                    <span className="font-medium text-ink">{ref.label}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  );
}

export function ResearchPanel() {
  const [topic, setTopic] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: "idle" });
  const [listState, setListState] = useState<ListState>({ kind: "loading" });

  function loadReports() {
    fetchResearchReports()
      .then((reports) => setListState({ kind: "ok", reports }))
      .catch((err) =>
        setListState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" })
      );
  }

  useEffect(() => {
    loadReports();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = topic.trim();
    if (!trimmed) return;

    setSubmitState({ kind: "loading" });
    try {
      await createResearchReport(trimmed);
      setTopic("");
      setSubmitState({ kind: "idle" });
      loadReports();
    } catch (err) {
      setSubmitState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" });
    }
  }

  return (
    <div className="flex w-full max-w-3xl flex-col gap-7">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
        <label htmlFor="topic" className="text-xs font-medium text-ink-muted">
          Research topic
        </label>
        <div className="flex gap-2.5">
          <input
            id="topic"
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. BHEL's tender activity versus Siemens Energy"
            className="flex-1 rounded border border-line bg-inset px-3.5 py-3 text-[13.5px] text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
          <button
            type="submit"
            disabled={submitState.kind === "loading" || !topic.trim()}
            className="rounded bg-accent px-5 font-semibold text-[13.5px] text-ink-onaccent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitState.kind === "loading" ? "Researching…" : "Research"}
          </button>
        </div>
        <p className="text-xs text-ink-faint">
          Searches documents, tenders, and knowledge-graph entities together and cites every claim
          against what it actually found.
        </p>
        {submitState.kind === "error" && (
          <div className="rounded-md border border-err/35 bg-err/10 p-3 text-sm text-err">{submitState.message}</div>
        )}
      </form>

      <div className="flex flex-col gap-3">
        <h2 className="font-mono text-[11px] tracking-wide text-ink-faint uppercase">Reports</h2>
        {listState.kind === "loading" && <p className="text-sm text-ink-muted">Loading…</p>}
        {listState.kind === "error" && (
          <div className="rounded-md border border-err/35 bg-err/10 p-4 text-sm text-err">{listState.message}</div>
        )}
        {listState.kind === "ok" && listState.reports.length === 0 && (
          <p className="text-sm text-ink-muted">No reports yet — research a topic above.</p>
        )}
        {listState.kind === "ok" && listState.reports.length > 0 && (
          <ul className="flex flex-col gap-2.5">
            {listState.reports.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
