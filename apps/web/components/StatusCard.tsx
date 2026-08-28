"use client";

import { useEffect, useState } from "react";
import { fetchStatus, type StatusResponse } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; status: StatusResponse };

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded px-3 py-1 font-mono text-[11px] font-medium tracking-wide uppercase ${
        ok ? "bg-ok/14 text-ok" : "bg-err/14 text-err"
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${ok ? "bg-ok" : "bg-err"}`} />
      {label}
    </span>
  );
}

export function StatusCard() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    fetchStatus()
      .then((status) => setState({ kind: "ok", status }))
      .catch((err) =>
        setState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" })
      );
  }, []);

  return (
    <div className="flex flex-col gap-3 rounded-md border border-line bg-surface p-5">
      <h2 className="font-mono text-[11px] tracking-wide text-ink-faint uppercase">System status</h2>
      {state.kind === "loading" && <p className="text-sm text-ink-muted">Checking API and database connectivity…</p>}
      {state.kind === "error" && (
        <div className="flex flex-col gap-2">
          <Badge ok={false} label="API unreachable" />
          <p className="text-sm text-err">{state.message}</p>
        </div>
      )}
      {state.kind === "ok" && (
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <Badge ok={state.status.api === "ok"} label="API" />
            <Badge ok={state.status.db === "ok"} label="Database" />
          </div>
          <p className="font-mono text-[10.5px] text-ink-faint">{state.status.timestamp}</p>
        </div>
      )}
    </div>
  );
}
