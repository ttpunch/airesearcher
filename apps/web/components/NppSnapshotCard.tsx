"use client";

import { useEffect, useState } from "react";
import { fetchNppCapacitySnapshot, type NppCapacitySnapshot } from "@/lib/api";
import { IconBolt } from "@/components/icons";

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ok"; snapshot: NppCapacitySnapshot };

function toGw(mw: number | null): string {
  if (mw === null) return "—";
  return (mw / 1000).toFixed(1);
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "unknown";
  return new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function NppSnapshotCard() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    fetchNppCapacitySnapshot()
      .then((snapshot) => setState({ kind: "ok", snapshot }))
      .catch((err) => setState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" }));
  }, []);

  return (
    <div className="relative flex max-w-sm flex-col gap-3.5 rounded-md border border-line bg-surface p-5">
      <span className="pointer-events-none absolute top-[-1px] left-[-1px] h-2.5 w-2.5 border-t-2 border-l-2 border-accent" />
      <span className="pointer-events-none absolute right-[-1px] bottom-[-1px] h-2.5 w-2.5 border-r-2 border-b-2 border-accent" />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <IconBolt className="h-4 w-4 text-accent" />
          <h2 className="font-display text-[13.5px] font-semibold text-ink">Power Data Synopsis</h2>
        </div>
        {state.kind === "ok" && (
          <span className="flex items-center gap-1.5 font-mono text-[9.5px] tracking-wide text-ok uppercase">
            <span className="h-1.5 w-1.5 rounded-full bg-ok" />
            Live
          </span>
        )}
      </div>

      {state.kind === "loading" && <p className="text-xs text-ink-muted">Fetching from National Power Portal…</p>}

      {state.kind === "error" && (
        <p className="text-xs text-err">National Power Portal unreachable — {state.message}</p>
      )}

      {state.kind === "ok" && (
        <>
          <div className="grid grid-cols-2 gap-2.5">
            <div className="flex flex-col gap-0.5">
              <span className="font-mono text-xl font-semibold text-ink">{toGw(state.snapshot.installed_capacity_mw)}</span>
              <span className="text-[10px] tracking-wide text-ink-faint uppercase">Installed GW</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="font-mono text-xl font-semibold text-ink">{toGw(state.snapshot.online_capacity_mw)}</span>
              <span className="text-[10px] tracking-wide text-ink-faint uppercase">Online GW</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="font-mono text-base font-medium text-ink-muted">
                {toGw(state.snapshot.under_maintenance_capacity_mw)}
              </span>
              <span className="text-[10px] tracking-wide text-ink-faint uppercase">Under maint. GW</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="font-mono text-base font-medium text-ink-muted">{toGw(state.snapshot.shutdown_capacity_mw)}</span>
              <span className="text-[10px] tracking-wide text-ink-faint uppercase">Shutdown GW</span>
            </div>
          </div>

          <div className="flex flex-col gap-1 border-t border-line pt-3 text-[10.5px] text-ink-faint">
            <span>Reporting date: {state.snapshot.reporting_date ? formatTimestamp(state.snapshot.reporting_date) : "unknown"}</span>
            <span>Fetched: {formatTimestamp(state.snapshot.retrieved_at)}</span>
            <a href="https://npp.gov.in/dashBoard/gc-map-dashboard" target="_blank" rel="noopener noreferrer" className="text-accent">
              Source: National Power Portal ↗
            </a>
          </div>
        </>
      )}
    </div>
  );
}
