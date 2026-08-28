"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Markdown } from "@/components/Markdown";
import {
  createResearchReport,
  fetchResearchReports,
  type Reference,
  type ResearchReport,
} from "@/lib/api";

type ListState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; reports: ResearchReport[] };

type SubmitState = { kind: "idle" } | { kind: "loading" } | { kind: "error"; message: string };

function StatusBadge({ status }: { status: string }) {
  if (status === "completed") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800 dark:bg-green-950 dark:text-green-300">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        Completed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-300">
      <span className="h-2 w-2 rounded-full bg-amber-500" />
      No evidence found
    </span>
  );
}

function ReferenceBadge({ refType }: { refType: string }) {
  const labels: Record<string, string> = { chunk: "document", tender: "tender", entity: "entity" };
  return (
    <span className="inline-flex items-center rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
      {labels[refType] ?? refType}
    </span>
  );
}

function ReportCard({ report }: { report: ResearchReport }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <li className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center justify-between gap-2 text-left"
      >
        <span className="font-medium text-zinc-900 dark:text-zinc-100">{report.topic}</span>
        <StatusBadge status={report.status} />
      </button>
      {expanded && (
        <div className="flex flex-col gap-3 border-t border-zinc-100 pt-3 dark:border-zinc-900">
          <Markdown>{report.summary}</Markdown>
          {report.references.length > 0 && (
            <ul className="flex flex-col gap-2">
              {report.references.map((ref: Reference) => (
                <li
                  key={`${ref.ref_type}-${ref.ref_id}`}
                  className="flex flex-col gap-1 rounded-md bg-zinc-50 p-2 text-xs dark:bg-zinc-900"
                >
                  <div className="flex items-center gap-2">
                    <ReferenceBadge refType={ref.ref_type} />
                    {ref.url ? (
                      <a
                        href={ref.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-zinc-900 underline decoration-zinc-300 hover:decoration-zinc-500 dark:text-zinc-100 dark:decoration-zinc-700"
                      >
                        {ref.label}
                      </a>
                    ) : (
                      <span className="font-medium text-zinc-900 dark:text-zinc-100">{ref.label}</span>
                    )}
                  </div>
                  {ref.detail && <p className="text-zinc-600 dark:text-zinc-400">{ref.detail}</p>}
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
    <div className="flex w-full flex-col gap-6">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label htmlFor="topic" className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
          Research topic
        </label>
        <div className="flex gap-2">
          <input
            id="topic"
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. BHEL's tender activity versus Siemens Energy"
            className="flex-1 rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-sm text-zinc-950 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-50"
          />
          <button
            type="submit"
            disabled={submitState.kind === "loading" || !topic.trim()}
            className="rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-300"
          >
            {submitState.kind === "loading" ? "Researching…" : "Research"}
          </button>
        </div>
        <p className="text-xs text-zinc-500 dark:text-zinc-500">
          Searches documents, tenders, and knowledge-graph entities together and cites every claim
          against what it actually found.
        </p>
        {submitState.kind === "error" && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {submitState.message}
          </div>
        )}
      </form>

      <div className="flex flex-col gap-3">
        <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
          Reports
        </h2>
        {listState.kind === "loading" && <p className="text-sm text-zinc-500">Loading…</p>}
        {listState.kind === "error" && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {listState.message}
          </div>
        )}
        {listState.kind === "ok" && listState.reports.length === 0 && (
          <p className="text-sm text-zinc-500">No reports yet — research a topic above.</p>
        )}
        {listState.kind === "ok" && listState.reports.length > 0 && (
          <ul className="flex flex-col gap-3">
            {listState.reports.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
