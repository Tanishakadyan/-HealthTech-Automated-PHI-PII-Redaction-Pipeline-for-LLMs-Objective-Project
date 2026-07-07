import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { RedactionResponse } from "@/lib/types/api";
import { HISTORY_LIMIT, type HistoryEntry } from "@/lib/types/history";

const HISTORY_KEY = "phi-guard:history";

function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as HistoryEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

interface HistoryContextValue {
  entries: HistoryEntry[];
  addEntry: (response: RedactionResponse, originalLength: number) => void;
  removeEntry: (id: string) => void;
  clearHistory: () => void;
  exportHistory: () => void;
}

const HistoryContext = createContext<HistoryContextValue | null>(null);

export function HistoryProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<HistoryEntry[]>(() => loadHistory());

  useEffect(() => {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  }, [entries]);

  const addEntry = useCallback((response: RedactionResponse, originalLength: number) => {
    const { status: _status, session_id, redacted_text, ...counts } = response;
    const entry: HistoryEntry = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      sessionId: session_id,
      redactedText: redacted_text,
      originalLength,
      counts,
    };
    setEntries((prev) => [entry, ...prev].slice(0, HISTORY_LIMIT));
  }, []);

  const removeEntry = useCallback(
    (id: string) => setEntries((prev) => prev.filter((entry) => entry.id !== id)),
    [],
  );

  const clearHistory = useCallback(() => setEntries([]), []);

  const exportHistory = useCallback(() => {
    setEntries((current) => {
      const blob = new Blob([JSON.stringify(current, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `phi-guard-history-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      return current;
    });
  }, []);

  const value = useMemo(
    () => ({ entries, addEntry, removeEntry, clearHistory, exportHistory }),
    [entries, addEntry, removeEntry, clearHistory, exportHistory],
  );

  return (
    <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>
  );
}

export function useHistory() {
  const ctx = useContext(HistoryContext);
  if (!ctx) throw new Error("useHistory must be used within HistoryProvider");
  return ctx;
}
