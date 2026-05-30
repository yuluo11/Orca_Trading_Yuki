import { Info } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center space-y-4">
      <Info className="w-12 h-12 text-zinc-500" />
      <div>
        <p className="font-medium text-zinc-300">No Insights Found</p>
        <p className="text-sm text-zinc-500 mt-1">The analysis returned empty results for the given input.</p>
      </div>
    </div>
  );
}
