"use client";

import { useEffect, useState } from "react";
import { approveOpportunity, fetchOpportunities, rejectOpportunity, type Opportunity } from "@/lib/api";

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ok"; opportunities: Opportunity[] };

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    proposed: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
    approved: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
    rejected: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}

function OpportunityCard({
  opportunity,
  onDecided,
}: {
  opportunity: Opportunity;
  onDecided: (updated: Opportunity) => void;
}) {
  const [approverName, setApproverName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDecision(action: "approve" | "reject") {
    if (!approverName.trim()) {
      setError("Enter a name before deciding.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated =
        action === "approve"
          ? await approveOpportunity(opportunity.id, approverName.trim())
          : await rejectOpportunity(opportunity.id, approverName.trim());
      onDecided(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-zinc-900 dark:text-zinc-100">{opportunity.title}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">score {opportunity.weighted_score}</span>
          <StatusBadge status={opportunity.status} />
        </div>
      </div>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{opportunity.description}</p>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500 dark:text-zinc-500">
        <span>Strategic value: {opportunity.strategic_value}</span>
        <span>Feasibility: {opportunity.feasibility}</span>
        <span>Timeline: {opportunity.timeline}</span>
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-500">{opportunity.tech_summary}</p>
      <p className="text-xs text-zinc-500 dark:text-zinc-500">Risk: {opportunity.risk}</p>

      {opportunity.status === "proposed" ? (
        <div className="flex flex-wrap items-center gap-2 border-t border-zinc-100 pt-2 dark:border-zinc-900">
          <input
            type="text"
            value={approverName}
            onChange={(e) => setApproverName(e.target.value)}
            placeholder="Your name"
            className="flex-1 rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs text-zinc-950 placeholder:text-zinc-400 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-50"
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => handleDecision("approve")}
            className="rounded-md bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => handleDecision("reject")}
            className="rounded-md bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      ) : (
        <p className="border-t border-zinc-100 pt-2 text-xs text-zinc-500 dark:border-zinc-900 dark:text-zinc-500">
          {opportunity.status === "approved" ? "Approved" : "Rejected"} by {opportunity.approved_by}
        </p>
      )}
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
    </li>
  );
}

export function OpportunitiesPanel() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    fetchOpportunities()
      .then((opportunities) => setState({ kind: "ok", opportunities }))
      .catch((err) =>
        setState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" })
      );
  }, []);

  function handleDecided(updated: Opportunity) {
    setState((prev) =>
      prev.kind === "ok"
        ? { kind: "ok", opportunities: prev.opportunities.map((o) => (o.id === updated.id ? updated : o)) }
        : prev
    );
  }

  if (state.kind === "loading") return <p className="text-sm text-zinc-500">Loading…</p>;
  if (state.kind === "error") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {state.message}
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {state.opportunities.map((opportunity) => (
        <OpportunityCard key={opportunity.id} opportunity={opportunity} onDecided={handleDecided} />
      ))}
    </ul>
  );
}
