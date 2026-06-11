import { ApiError } from "./fetch";
import { API_BASE_URL } from "./client";

export const BACKEND_UNAVAILABLE_MESSAGE = `Backend API is unavailable. Make sure the backend is running and accessible at ${API_BASE_URL.replace('/api', '')}.`;

export function isBackendUnavailableError(error: unknown): boolean {
  if (error instanceof ApiError && error.status === 0) return true;
  if (error instanceof Error) {
    return error.message.includes("Failed to fetch") || error.message.includes("Network Error");
  }
  return false;
}

export function shouldRetryApiQuery(failureCount: number, error: unknown): boolean {
  if (isBackendUnavailableError(error)) return false;
  return failureCount < 3;
}
