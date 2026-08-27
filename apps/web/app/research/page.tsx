import { AppShell } from "@/components/AppShell";
import { ResearchPanel } from "@/components/ResearchPanel";

export default function ResearchPage() {
  return (
    <AppShell
      breadcrumb="DEEP RESEARCH"
      title="Deep Research"
      description="Multi-source research reports — the agent searches documents, tenders, and knowledge-graph entities together, citing every claim against what it actually retrieved."
    >
      <ResearchPanel />
    </AppShell>
  );
}
