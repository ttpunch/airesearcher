import { AppShell } from "@/components/AppShell";
import { EntityList } from "@/components/EntityList";

export default function TechnologiesPage() {
  return (
    <AppShell
      breadcrumb="TECHNOLOGIES"
      title="Technology Intelligence"
      description="Technology concepts named as relevant to BHEL in the strategy report's AI-landscape research — knowledge-graph nodes, not crawlable sources."
    >
      <EntityList entityType="technology" emptyMessage="No technology entities indexed yet." />
    </AppShell>
  );
}
