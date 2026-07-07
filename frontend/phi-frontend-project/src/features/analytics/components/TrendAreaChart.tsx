import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { computeDailyBuckets } from "@/lib/historyStats";
import type { HistoryEntry } from "@/lib/types/history";

export function TrendAreaChart({ entries }: { entries: HistoryEntry[] }) {
  const buckets = computeDailyBuckets(entries, 14);

  return (
    <Card>
      <CardHeader>
        <CardTitle>14-day trend</CardTitle>
        <CardDescription>Total entities redacted per day.</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={buckets} margin={{ left: -20 }}>
            <defs>
              <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0891B2" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#0891B2" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--border))" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: "rgb(var(--muted-foreground))" }}
              axisLine={{ stroke: "rgb(var(--border))" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "rgb(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid rgb(var(--border))",
                background: "rgb(var(--popover))",
                color: "rgb(var(--popover-foreground))",
                fontSize: 12,
              }}
            />
            <Area type="monotone" dataKey="entities" stroke="#0891B2" strokeWidth={2} fill="url(#trendFill)" />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
