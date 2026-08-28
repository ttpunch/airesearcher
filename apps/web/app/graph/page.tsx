import { AppShell } from "@/components/AppShell";
import { GraphPanel } from "@/components/GraphPanel";

export default function GraphPage() {
  return (
    <AppShell
      breadcrumb="KNOWLEDGE GRAPH"
      title="Knowledge Graph"
      description="Entities grouped by type and the relationships between them — a list/table view, not a graph-visual UI (out of scope for V1, see AGENTS.md)."
    >
      <GraphPanel />
    </AppShell>
  );
}
