import { Link } from "react-router-dom";
import { Eraser } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { StatsGrid } from "@/features/dashboard/components/StatsGrid";
import { EntityPieChart } from "@/features/dashboard/components/EntityPieChart";
import { ActivityBarChart } from "@/features/dashboard/components/ActivityBarChart";
import { RecentActivityList } from "@/features/dashboard/components/RecentActivityList";
import { useHistory } from "@/lib/hooks/useHistory";

export default function DashboardPage() {
  const { entries } = useHistory();

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        description="A snapshot of redaction activity tracked locally in this browser."
        actions={
          <Button asChild>
            <Link to="/redact">
              <Eraser /> New redaction
            </Link>
          </Button>
        }
      />

      <StatsGrid entries={entries} />

      <div className="grid gap-6 lg:grid-cols-2">
        <EntityPieChart entries={entries} />
        <ActivityBarChart entries={entries} />
      </div>

      <RecentActivityList entries={entries} />
    </div>
  );
}
