import { AppShell } from "@/components/AppShell";
import { AskPanel } from "@/components/AskPanel";

export default function AskPage() {
  return (
    <AppShell
      breadcrumb="ASK AI"
      title="Ask AI"
      description="Research assistant over BHEL public sources — every claim is cited and checked against what was actually retrieved."
    >
      <AskPanel />
    </AppShell>
  );
}
