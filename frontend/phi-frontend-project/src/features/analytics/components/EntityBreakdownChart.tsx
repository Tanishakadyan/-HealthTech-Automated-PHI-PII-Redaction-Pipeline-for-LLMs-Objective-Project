import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { BarChart3 } from "lucide-react";
import { ENTITY_META } from "@/lib/constants/entities";
import { computeEntityTotals } from "@/lib/historyStats";
import type { HistoryEntry } from "@/lib/types/history";

export function EntityBreakdownChart({ entries }: { entries: HistoryEntry[] }) {
  const totals = computeEntityTotals(entries)
    .filter((t) => t.total > 0)
    .sort((a, b) => b.total - a.total)
    .map((t) => ({
      name: ENTITY_META[t.key].shortLabel,
      value: t.total,
      color: ENTITY_META[t.key].color,
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Full entity breakdown</CardTitle>
        <CardDescription>Every entity type detected, most frequent first.</CardDescription>
      </CardHeader>
      <CardContent>
        {totals.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No data yet"
            description="Analytics populate automatically as you redact text."
            className="border-none py-8"
          />
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(280, totals.length * 34)}>
            <BarChart data={totals} layout="vertical" margin={{ left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--border))" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 12, fill: "rgb(var(--muted-foreground))" }}
                axisLine={{ stroke: "rgb(var(--border))" }}
                tickLine={false}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={100}
                tick={{ fontSize: 12, fill: "rgb(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgb(var(--muted) / 0.5)" }}
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid rgb(var(--border))",
                  background: "rgb(var(--popover))",
                  color: "rgb(var(--popover-foreground))",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {totals.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
