import { Link } from "react-router-dom";
import { Clock3, ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { formatRelativeTime, truncate } from "@/lib/utils";
import type { HistoryEntry } from "@/lib/types/history";

export function RecentActivityList({ entries }: { entries: HistoryEntry[] }) {
  const recent = entries.slice(0, 6);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Recent activity</CardTitle>
          <CardDescription>Your last {recent.length || 0} redaction requests.</CardDescription>
        </div>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/history">
            View all <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {recent.length === 0 ? (
          <EmptyState
            icon={Clock3}
            title="No activity yet"
            description="Redacted requests will show up here as you use the tool."
            className="border-none py-8"
          />
        ) : (
          <ul className="divide-y divide-border/70">
            {recent.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <p className="truncate font-data text-sm text-foreground/90">
                    {truncate(entry.redactedText, 64)}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {formatRelativeTime(entry.createdAt)} · session {entry.sessionId.slice(0, 8)}…
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
