import { AppShell } from "@/components/AppShell";
import { OpportunitiesPanel } from "@/components/OpportunitiesPanel";

export default function OpportunitiesPage() {
  return (
    <AppShell
      breadcrumb="OPPORTUNITIES"
      title="Opportunity Engine"
      description="The strategy report's Top 10 strategic initiatives, ranked by weighted score. Recommendation-tagged — nothing here acts until a human approves it."
    >
      <OpportunitiesPanel />
    </AppShell>
  );
}
