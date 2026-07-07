import type { RedactionResponse } from "@/lib/types/api";

/**
 * A history entry deliberately never stores the original clinical text —
 * only the pseudonymized (already-redacted) output and its entity counts.
 * The session_id lets the user jump to Restore while the backend session
 * is still alive (30 minute TTL, enforced server-side).
 */
export interface HistoryEntry {
  id: string;
  createdAt: string;
  sessionId: string;
  redactedText: string;
  originalLength: number;
  counts: Omit<RedactionResponse, "status" | "session_id" | "redacted_text">;
}

export const HISTORY_LIMIT = 20;
