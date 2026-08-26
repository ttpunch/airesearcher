"use client";

import { useEffect, useState } from "react";
import { fetchAllEntities, fetchRelationships, type Entity, type Relationship } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; entities: Entity[]; relationships: Relationship[] };

export function GraphPanel() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    Promise.all([fetchAllEntities(), fetchRelationships()])
      .then(([entities, relationships]) => setState({ kind: "ok", entities, relationships }))
      .catch((err) =>
        setState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" })
      );
  }, []);

  if (state.kind === "loading") return <p className="text-sm text-zinc-500">Loading…</p>;
  if (state.kind === "error") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {state.message}
      </div>
    );
  }

  const byType = new Map<string, Entity[]>();
  for (const entity of state.entities) {
    const list = byType.get(entity.entity_type) ?? [];
    list.push(entity);
    byType.set(entity.entity_type, list);
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4">
        <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
          Entities ({state.entities.length})
        </h2>
        {[...byType.entries()].map(([entityType, entities]) => (
          <div key={entityType} className="flex flex-col gap-2">
            <h3 className="text-sm font-medium capitalize text-zinc-700 dark:text-zinc-300">{entityType}</h3>
            <ul className="flex flex-wrap gap-2">
              {entities.map((entity) => (
                <li
                  key={entity.id}
                  className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                >
                  {entity.name}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-2">
        <h2 className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
          Relationships ({state.relationships.length})
        </h2>
        <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs uppercase text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
              <tr>
                <th className="px-3 py-2">From</th>
                <th className="px-3 py-2">Relation</th>
                <th className="px-3 py-2">To</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
              {state.relationships.map((rel) => (
                <tr key={rel.id}>
                  <td className="px-3 py-2 text-zinc-900 dark:text-zinc-100">{rel.from_entity_name}</td>
                  <td className="px-3 py-2 text-zinc-500 dark:text-zinc-500">{rel.relation_type}</td>
                  <td className="px-3 py-2 text-zinc-900 dark:text-zinc-100">{rel.to_entity_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
