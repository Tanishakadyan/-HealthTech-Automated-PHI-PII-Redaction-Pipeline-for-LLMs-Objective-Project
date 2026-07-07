import { isSameDay } from "@/lib/utils";
import { ENTITY_COUNT_KEYS, type EntityCountKey } from "@/lib/types/api";
import type { HistoryEntry } from "@/lib/types/history";

export interface EntityTotal {
  key: EntityCountKey;
  total: number;
}

export function computeEntityTotals(entries: HistoryEntry[]): EntityTotal[] {
  return ENTITY_COUNT_KEYS.map((key) => ({
    key,
    total: entries.reduce((sum, entry) => sum + (entry.counts[key] ?? 0), 0),
  }));
}

export function computeTotalRedactions(entries: HistoryEntry[]): number {
  return entries.reduce(
    (sum, entry) => sum + ENTITY_COUNT_KEYS.reduce((s, k) => s + (entry.counts[k] ?? 0), 0),
    0,
  );
}

export function computeTodayCount(entries: HistoryEntry[]): number {
  const now = new Date().toISOString();
  return entries.filter((entry) => isSameDay(entry.createdAt, now)).length;
}

export interface DailyBucket {
  date: string;
  label: string;
  requests: number;
  entities: number;
}

/** Buckets history entries into the last N days (oldest -> newest) for bar/timeline charts. */
export function computeDailyBuckets(entries: HistoryEntry[], days = 7): DailyBucket[] {
  const buckets: DailyBucket[] = [];
  const today = new Date();

  for (let i = days - 1; i >= 0; i--) {
    const day = new Date(today);
    day.setDate(today.getDate() - i);
    const dayIso = day.toISOString();

    const dayEntries = entries.filter((entry) => isSameDay(entry.createdAt, dayIso));
    const entityCount = dayEntries.reduce(
      (sum, entry) => sum + ENTITY_COUNT_KEYS.reduce((s, k) => s + (entry.counts[k] ?? 0), 0),
      0,
    );

    buckets.push({
      date: dayIso,
      label: day.toLocaleDateString("en-US", { weekday: "short" }),
      requests: dayEntries.length,
      entities: entityCount,
    });
  }

  return buckets;
}
