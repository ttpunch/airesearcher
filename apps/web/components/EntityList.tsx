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
    return <p className="text-sm text-ink-muted">Loading…</p>;
  }

  if (state.kind === "error") {
    return <div className="rounded-md border border-err/35 bg-err/10 p-4 text-sm text-err">{state.message}</div>;
  }

  if (state.entities.length === 0) {
    return <p className="text-sm text-ink-muted">{emptyMessage}</p>;
  }

  return (
    <ul className="grid max-w-3xl grid-cols-1 gap-3.5 sm:grid-cols-2">
      {state.entities.map((entity) => (
        <li key={entity.id} className="relative flex flex-col gap-2.5 rounded-md border border-line bg-surface p-5">
          <span className="pointer-events-none absolute top-[-1px] left-[-1px] h-2.5 w-2.5 border-t-2 border-l-2 border-accent" />
          <span className="pointer-events-none absolute right-[-1px] bottom-[-1px] h-2.5 w-2.5 border-r-2 border-b-2 border-accent" />
          <div className="flex items-center justify-between">
            {entity.source_url ? (
              <a
                href={entity.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-display font-semibold text-ink underline-offset-2 hover:underline"
              >
                {entity.name}
              </a>
            ) : (
              <span className="font-display font-semibold text-ink">{entity.name}</span>
            )}
            <span className="rounded border border-info/35 bg-info/14 px-2 py-0.5 font-mono text-[10px] tracking-wide text-info uppercase">
              {entity.entity_type}
            </span>
          </div>
          {entity.description && <p className="text-[12.5px] leading-relaxed text-ink-faint">{entity.description}</p>}
          {entity.source_url && (
            <a
              href={entity.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[12.5px] text-accent"
            >
              {entity.source_url.replace(/^https?:\/\//, "")} ↗
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
