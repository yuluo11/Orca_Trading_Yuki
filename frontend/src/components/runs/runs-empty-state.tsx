import { Activity, SearchX } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface RunsEmptyStateProps {
  isFiltered: boolean;
  onClear?: () => void;
}

export function RunsEmptyState({ isFiltered, onClear }: RunsEmptyStateProps) {
  if (isFiltered) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center border border-dashed border-zinc-800 rounded-lg bg-zinc-900/20">
        <div className="w-16 h-16 mb-4 rounded-full bg-zinc-800/50 flex items-center justify-center">
          <SearchX className="w-8 h-8 text-zinc-500" />
        </div>
        <h3 className="text-xl font-semibold text-zinc-200 mb-2">No matches found</h3>
        <p className="text-zinc-500 mb-6 max-w-sm">
          We could not find any runs matching your current filters. Try adjusting your search or clearing the filters.
        </p>
        <Button onClick={onClear} variant="outline" className="border-zinc-700 hover:bg-zinc-800">
          Clear Filters
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center border border-dashed border-zinc-800 rounded-lg bg-zinc-900/20">
      <div className="w-16 h-16 mb-4 rounded-full bg-blue-500/10 flex items-center justify-center">
        <Activity className="w-8 h-8 text-blue-400" />
      </div>
      <h3 className="text-xl font-semibold text-zinc-200 mb-2">No analysis runs yet</h3>
      <p className="text-zinc-500 mb-6 max-w-sm">
        You have not run any analysis tasks. Get started by creating your first one from the workbench.
      </p>
      <Link href="/">
        <Button className="bg-blue-600 hover:bg-blue-700 text-white">
          New Analysis
        </Button>
      </Link>
    </div>
  );
}
