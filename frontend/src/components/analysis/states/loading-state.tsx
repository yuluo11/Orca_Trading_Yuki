import { Loader2 } from "lucide-react";

export function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 space-y-4">
      <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
      <p className="text-sm text-zinc-400 animate-pulse">Running multi-dimensional analysis...</p>
    </div>
  );
}
