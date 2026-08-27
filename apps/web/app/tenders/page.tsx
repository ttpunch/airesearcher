import { AppShell } from "@/components/AppShell";
import { TendersPanel } from "@/components/TendersPanel";

export default function TendersPage() {
  return (
    <AppShell
      breadcrumb="TENDERS"
      title="Tender Intelligence"
      description="Tenders discovered from registered sources, with deterministic requirement extraction and a bid-pattern summary over what's actually indexed."
    >
      <TendersPanel />
    </AppShell>
  );
}
