import { AlertCircle } from "lucide-react";

export function ErrorState({ error }: { error: Error }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center space-y-4">
      <AlertCircle className="w-12 h-12 text-red-500/80" />
      <div>
        <p className="text-red-400 font-medium">Analysis Failed</p>
        <p className="text-sm text-zinc-500 mt-1">{error.message || "An unexpected error occurred."}</p>
      </div>
    </div>
  );
}
