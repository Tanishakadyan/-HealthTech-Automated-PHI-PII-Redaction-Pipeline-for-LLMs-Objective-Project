import { apiClient, toApiError } from "@/lib/api/client";
import type { HealthResponse, RedactionResponse, RestoreResponse } from "@/lib/types/api";

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const { data } = await apiClient.get<HealthResponse>("/health");
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function redactText(text: string): Promise<RedactionResponse> {
  try {
    const { data } = await apiClient.post<RedactionResponse>("/redact", { text });
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function restoreText(
  sessionId: string,
  text: string,
): Promise<RestoreResponse> {
  try {
    const { data } = await apiClient.post<RestoreResponse>("/restore", {
      session_id: sessionId,
      text,
    });
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}
