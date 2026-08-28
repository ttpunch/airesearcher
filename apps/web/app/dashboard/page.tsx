import { AppShell } from "@/components/AppShell";
import { DashboardPanel } from "@/components/DashboardPanel";

export default function DashboardPage() {
  return (
    <AppShell
      breadcrumb="DASHBOARD"
      title="Dashboard"
      description="What's indexed across the platform, and the highest-scored strategic opportunities."
    >
      <DashboardPanel />
    </AppShell>
  );
}
