import { AlertCircle } from "lucide-react";
import { isBackendUnavailableError, BACKEND_UNAVAILABLE_MESSAGE } from "@/lib/api/errors";

export function ErrorState({ error }: { error: Error }) {
  const isNetworkError = isBackendUnavailableError(error);

  return (
    <div className="flex flex-col items-center justify-center h-64 text-center space-y-4 px-4">
      <AlertCircle className="w-12 h-12 text-red-500/80" />
      <div>
        <p className="text-red-400 font-medium">
          {isNetworkError ? "Backend API is unavailable." : "Analysis Failed"}
        </p>
        <p className="text-sm text-zinc-500 mt-1">
          {isNetworkError
            ? BACKEND_UNAVAILABLE_MESSAGE
            : error.message || "An unexpected error occurred."}
        </p>
      </div>
    </div>
  );
}
