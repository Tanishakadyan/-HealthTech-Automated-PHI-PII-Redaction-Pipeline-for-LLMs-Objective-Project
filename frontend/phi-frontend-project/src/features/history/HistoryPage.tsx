import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Download, History as HistoryIcon, RotateCcw, Search, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { CopyButton } from "@/components/shared/CopyButton";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useHistory } from "@/lib/hooks/useHistory";
import { formatDateTime, truncate } from "@/lib/utils";
import { ENTITY_META } from "@/lib/constants/entities";
import { ENTITY_COUNT_KEYS, type EntityCountKey } from "@/lib/types/api";

export default function HistoryPage() {
  const { entries, removeEntry, clearHistory, exportHistory } = useHistory();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [entityFilter, setEntityFilter] = useState<EntityCountKey | "all">("all");

  const filtered = useMemo(() => {
    return entries.filter((entry) => {
      const matchesQuery =
        query.trim().length === 0 ||
        entry.redactedText.toLowerCase().includes(query.toLowerCase()) ||
        entry.sessionId.toLowerCase().includes(query.toLowerCase());
      const matchesEntity = entityFilter === "all" || (entry.counts[entityFilter] ?? 0) > 0;
      return matchesQuery && matchesEntity;
    });
  }, [entries, query, entityFilter]);

  const handleRestore = (sessionId: string, redactedText: string) => {
    navigate("/restore", { state: { sessionId, redactedText } });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Records"
        title="History"
        description={`Your last ${entries.length} redaction requests, stored only in this browser.`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={exportHistory} disabled={entries.length === 0}>
              <Download /> Export JSON
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" disabled={entries.length === 0}>
                  <Trash2 /> Clear all
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Clear all history?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This removes all {entries.length} stored entries from this browser. This can't
                    be undone, but active backend sessions are unaffected.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => {
                      clearHistory();
                      toast.success("History cleared");
                    }}
                  >
                    Clear history
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search redacted text or session ID…"
            className="pl-9"
          />
        </div>
        <Select value={entityFilter} onValueChange={(v) => setEntityFilter(v as EntityCountKey | "all")}>
          <SelectTrigger className="sm:w-56">
            <SelectValue placeholder="Filter by entity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All entity types</SelectItem>
            {ENTITY_COUNT_KEYS.map((key) => (
              <SelectItem key={key} value={key}>
                {ENTITY_META[key].label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={HistoryIcon}
          title={entries.length === 0 ? "No history yet" : "No matches"}
          description={
            entries.length === 0
              ? "Redacted requests appear here automatically, most recent first."
              : "Try a different search term or filter."
          }
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((entry) => {
            const activeEntities = ENTITY_COUNT_KEYS.filter((k) => (entry.counts[k] ?? 0) > 0);
            return (
              <Card key={entry.id}>
                <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-data text-sm text-foreground/90">
                      {truncate(entry.redactedText, 90)}
                    </p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      <span>{formatDateTime(entry.createdAt)}</span>
                      <span className="font-data">session {entry.sessionId.slice(0, 8)}…</span>
                      <span>{entry.originalLength.toLocaleString()} chars</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {activeEntities.slice(0, 5).map((key) => (
                        <Badge key={key} variant="muted">
                          {ENTITY_META[key].shortLabel} · {entry.counts[key]}
                        </Badge>
                      ))}
                      {activeEntities.length > 5 && (
                        <Badge variant="muted">+{activeEntities.length - 5} more</Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <CopyButton text={entry.redactedText} label="Copy" />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRestore(entry.sessionId, entry.redactedText)}
                    >
                      <RotateCcw /> Restore
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete entry"
                      onClick={() => {
                        removeEntry(entry.id);
                        toast("Entry removed");
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
