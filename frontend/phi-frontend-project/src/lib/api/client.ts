import axios, { AxiosError } from "axios";
import { getStoredBackendUrl } from "@/lib/hooks/useSettings";
import type { ApiErrorPayload } from "@/lib/types/api";

export const apiClient = axios.create({
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// The backend URL is user-configurable from Settings, so it's resolved
// fresh on every request rather than baked in at client-creation time.
apiClient.interceptors.request.use((config) => {
  config.baseURL = getStoredBackendUrl();
  return config;
});

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorPayload>;
    const status = axiosError.response?.status;
    const payload = axiosError.response?.data;

    if (status === 429) {
      return new ApiError(
        "Rate limit reached. Wait a moment before trying again.",
        429,
      );
    }
    if (status === 404) {
      return new ApiError(
        payload?.detail as string ?? "Session not found or expired.",
        404,
      );
    }
    if (status === 422) {
      const detail = payload?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(", ")
        : (detail as string) ?? "Validation error.";
      return new ApiError(message, 422);
    }
    if (axiosError.code === "ECONNABORTED") {
      return new ApiError("Request timed out. Check the backend URL in Settings.");
    }
    if (!axiosError.response) {
      return new ApiError(
        "Could not reach the backend. Check the backend URL in Settings and that the API is running.",
      );
    }
    return new ApiError(
      payload?.message ?? axiosError.message ?? "Unexpected error.",
      status,
    );
  }
  return new ApiError("Unexpected error.");
}
