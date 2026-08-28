"use client";

import { useEffect, useState } from "react";
import { approveOpportunity, fetchOpportunities, rejectOpportunity, type Opportunity } from "@/lib/api";

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ok"; opportunities: Opportunity[] };

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    proposed: "bg-warn/14 text-warn border-warn/35",
    approved: "bg-ok/14 text-ok border-ok/35",
    rejected: "bg-err/14 text-err border-err/35",
  };
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[10.5px] font-medium tracking-wide uppercase ${styles[status]}`}>
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
    <li className="flex flex-col gap-2.5 rounded-md border border-line bg-surface p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold text-ink">{opportunity.title}</span>
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-[13px] text-accent">{opportunity.weighted_score}</span>
          <StatusBadge status={opportunity.status} />
        </div>
      </div>
      <p className="text-sm leading-relaxed text-ink-muted">{opportunity.description}</p>
      <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-line pt-2.5 text-[11.5px] text-ink-faint">
        <span>
          Strategic value: <span className="font-mono text-ink-muted">{opportunity.strategic_value}</span>
        </span>
        <span>
          Feasibility: <span className="font-mono text-ink-muted">{opportunity.feasibility}</span>
        </span>
        <span>
          Timeline: <span className="font-mono text-ink-muted">{opportunity.timeline}</span>
        </span>
      </div>
      <p className="text-xs text-ink-faint">{opportunity.tech_summary}</p>
      <p className="text-xs text-ink-faint">Risk: {opportunity.risk}</p>

      {opportunity.status === "proposed" ? (
        <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <input
            type="text"
            value={approverName}
            onChange={(e) => setApproverName(e.target.value)}
            placeholder="Your name"
            className="flex-1 rounded border border-line bg-inset px-2.5 py-1.5 text-xs text-ink placeholder:text-ink-faint"
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => handleDecision("approve")}
            className="rounded bg-ok px-3 py-1.5 text-xs font-semibold text-ink-onaccent disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => handleDecision("reject")}
            className="rounded border border-err/40 px-3 py-1.5 text-xs font-semibold text-err disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      ) : (
        <p className="border-t border-line pt-2.5 text-xs text-ink-faint">
          {opportunity.status === "approved" ? "Approved" : "Rejected"} by {opportunity.approved_by}
        </p>
      )}
      {error && <p className="text-xs text-err">{error}</p>}
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

  if (state.kind === "loading") return <p className="text-sm text-ink-muted">Loading…</p>;
  if (state.kind === "error") {
    return <div className="rounded-md border border-err/35 bg-err/10 p-4 text-sm text-err">{state.message}</div>;
  }

  return (
    <ul className="flex max-w-3xl flex-col gap-2.5">
      {state.opportunities.map((opportunity) => (
        <OpportunityCard key={opportunity.id} opportunity={opportunity} onDecided={handleDecided} />
      ))}
    </ul>
  );
}
