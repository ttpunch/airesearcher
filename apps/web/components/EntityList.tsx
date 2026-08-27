"use client";

import { useEffect, useState } from "react";
import { fetchEntities, type Entity } from "@/lib/api";

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ok"; entities: Entity[] };

export function EntityList({ entityType, emptyMessage }: { entityType: string; emptyMessage: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    fetchEntities(entityType)
      .then((entities) => setState({ kind: "ok", entities }))
      .catch((err) =>
        setState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" })
      );
  }, [entityType]);

  if (state.kind === "loading") {
    return <p className="text-sm text-zinc-500">Loading…</p>;
  }

  if (state.kind === "error") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {state.message}
      </div>
    );
  }

  if (state.entities.length === 0) {
    return <p className="text-sm text-zinc-500">{emptyMessage}</p>;
  }

  return (
    <ul className="flex flex-col gap-3">
      {state.entities.map((entity) => (
        <li
          key={entity.id}
          className="flex flex-col gap-1.5 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
        >
          {entity.source_url ? (
            <a
              href={entity.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-zinc-900 underline decoration-zinc-300 hover:decoration-zinc-500 dark:text-zinc-100 dark:decoration-zinc-700"
            >
              {entity.name}
            </a>
          ) : (
            <span className="font-medium text-zinc-900 dark:text-zinc-100">{entity.name}</span>
          )}
          {entity.description && (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{entity.description}</p>
          )}
        </li>
      ))}
    </ul>
  );
}
