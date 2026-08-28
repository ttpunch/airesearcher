import { AppShell } from "@/components/AppShell";
import { EntityList } from "@/components/EntityList";

export default function CompetitorsPage() {
  return (
    <AppShell
      breadcrumb="COMPETITORS"
      title="Competitor Intelligence"
      description="Organizations overlapping BHEL's power and industrial equipment segments, sourced from their official sites (domains verified live, not guessed)."
    >
      <EntityList entityType="competitor" emptyMessage="No competitor entities indexed yet." />
    </AppShell>
  );
}
