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
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${
        ok
          ? "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300"
          : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`} />
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
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">System status</h2>
      {state.kind === "loading" && (
        <p className="text-sm text-zinc-500">Checking API and database connectivity…</p>
      )}
      {state.kind === "error" && (
        <div className="flex flex-col gap-2">
          <Badge ok={false} label="API unreachable" />
          <p className="text-sm text-red-600 dark:text-red-400">{state.message}</p>
        </div>
      )}
      {state.kind === "ok" && (
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <Badge ok={state.status.api === "ok"} label="API" />
            <Badge ok={state.status.db === "ok"} label="Database" />
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-500">{state.status.timestamp}</p>
        </div>
      )}
    </div>
  );
}
