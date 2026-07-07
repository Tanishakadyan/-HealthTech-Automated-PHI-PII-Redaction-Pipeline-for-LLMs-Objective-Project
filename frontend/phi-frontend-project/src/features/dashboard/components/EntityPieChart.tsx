import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { PieChart as PieIcon } from "lucide-react";
import { ENTITY_META } from "@/lib/constants/entities";
import { computeEntityTotals } from "@/lib/historyStats";
import type { HistoryEntry } from "@/lib/types/history";

export function EntityPieChart({ entries }: { entries: HistoryEntry[] }) {
  const totals = computeEntityTotals(entries)
    .filter((t) => t.total > 0)
    .map((t) => ({ name: ENTITY_META[t.key].shortLabel, value: t.total, color: ENTITY_META[t.key].color }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Entity distribution</CardTitle>
        <CardDescription>Share of each PHI/PII type across all redactions.</CardDescription>
      </CardHeader>
      <CardContent>
        {totals.length === 0 ? (
          <EmptyState
            icon={PieIcon}
            title="No data yet"
            description="Run a few redactions to populate this chart."
            className="border-none py-8"
          />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={totals}
                dataKey="value"
                nameKey="name"
                innerRadius={64}
                outerRadius={98}
                paddingAngle={2}
                strokeWidth={2}
              >
                {totals.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} stroke="transparent" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid rgb(var(--border))",
                  background: "rgb(var(--popover))",
                  color: "rgb(var(--popover-foreground))",
                  fontSize: 12,
                }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                wrapperStyle={{ fontSize: 12, color: "rgb(var(--muted-foreground))" }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
