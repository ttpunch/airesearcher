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

  if (state.kind === "loading") return <p className="text-sm text-ink-muted">Loading…</p>;
  if (state.kind === "error") {
    return <div className="rounded-md border border-err/35 bg-err/10 p-4 text-sm text-err">{state.message}</div>;
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
        <h2 className="font-mono text-[11px] tracking-wide text-ink-faint uppercase">
          Entities ({state.entities.length})
        </h2>
        {[...byType.entries()].map(([entityType, entities]) => (
          <div key={entityType} className="flex flex-col gap-2">
            <h3 className="text-[13px] font-semibold text-ink-muted capitalize">{entityType}</h3>
            <ul className="flex flex-wrap gap-2">
              {entities.map((entity) => (
                <li
                  key={entity.id}
                  className={`rounded border px-3 py-1.5 text-xs font-medium ${
                    entity.entity_type === "organization"
                      ? "border-accent bg-accent/14 text-accent"
                      : "border-line bg-surface-2 text-ink-muted"
                  }`}
                >
                  {entity.name}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="flex max-w-3xl flex-col gap-2">
        <h2 className="font-mono text-[11px] tracking-wide text-ink-faint uppercase">
          Relationships ({state.relationships.length})
        </h2>
        <div className="overflow-x-auto rounded-md border border-line">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-2 font-mono text-[10.5px] tracking-wide text-ink-faint uppercase">
              <tr>
                <th className="px-3.5 py-2.5">From</th>
                <th className="px-3.5 py-2.5">Relation</th>
                <th className="px-3.5 py-2.5">To</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {state.relationships.map((rel) => (
                <tr key={rel.id}>
                  <td className="px-3.5 py-2.5 font-medium text-ink">{rel.from_entity_name}</td>
                  <td className="px-3.5 py-2.5 font-mono text-[12px] text-accent">{rel.relation_type}</td>
                  <td className="px-3.5 py-2.5 font-medium text-ink">{rel.to_entity_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
