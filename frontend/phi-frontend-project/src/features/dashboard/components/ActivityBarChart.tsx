import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { computeDailyBuckets } from "@/lib/historyStats";
import type { HistoryEntry } from "@/lib/types/history";

export function ActivityBarChart({ entries }: { entries: HistoryEntry[] }) {
  const buckets = computeDailyBuckets(entries, 7);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity timeline</CardTitle>
        <CardDescription>Requests and entities detected over the last 7 days.</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={buckets} margin={{ left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--border))" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12, fill: "rgb(var(--muted-foreground))" }}
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
            <Bar dataKey="requests" name="Requests" fill="#0891B2" radius={[4, 4, 0, 0]} maxBarSize={28} />
            <Bar dataKey="entities" name="Entities found" fill="#059669" radius={[4, 4, 0, 0]} maxBarSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
