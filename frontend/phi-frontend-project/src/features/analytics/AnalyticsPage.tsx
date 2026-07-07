import { PageHeader } from "@/components/shared/PageHeader";
import { EntityBreakdownChart } from "@/features/analytics/components/EntityBreakdownChart";
import { TrendAreaChart } from "@/features/analytics/components/TrendAreaChart";
import { EntityPieChart } from "@/features/dashboard/components/EntityPieChart";
import { useHistory } from "@/lib/hooks/useHistory";
import { computeTotalRedactions } from "@/lib/historyStats";
import { Card, CardContent } from "@/components/ui/card";

export default function AnalyticsPage() {
  const { entries } = useHistory();
  const total = computeTotalRedactions(entries);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Insights"
        title="Analytics"
        description="Deeper breakdowns of what's been detected across your recent redaction requests."
      />

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <p className="text-sm text-muted-foreground">Tracked requests (this browser)</p>
            <p className="font-data text-2xl font-semibold">{entries.length}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Total entities redacted</p>
            <p className="font-data text-2xl font-semibold">{total}</p>
          </div>
          <p className="max-w-sm text-xs text-muted-foreground">
            Analytics are derived from the last 20 requests stored locally in this browser — no
            original text is kept, only redacted output and counts.
          </p>
        </CardContent>
      </Card>

      <TrendAreaChart entries={entries} />

      <div className="grid gap-6 lg:grid-cols-2">
        <EntityPieChart entries={entries} />
        <EntityBreakdownChart entries={entries} />
      </div>
    </div>
  );
}
