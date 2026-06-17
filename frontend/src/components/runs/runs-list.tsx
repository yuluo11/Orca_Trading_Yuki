import { Card, CardContent } from "@/components/ui/card";
import { HistoryRun } from "@/lib/api/types";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { RunStatusBadge, RunStatusIcon } from "./run-status-badge";
import { RunsEmptyState } from "./runs-empty-state";

interface RunsListProps {
  runs: HistoryRun[];
  totalRuns?: number;
  onClearFilters?: () => void;
}

export function RunsList({ runs, totalRuns, onClearFilters }: RunsListProps) {
  if (runs.length === 0) {
    const isFiltered = totalRuns !== undefined && totalRuns > 0;
    return <RunsEmptyState isFiltered={isFiltered} onClear={onClearFilters} />;
  }

  return (
    <div className="space-y-4">
      {runs.map((run) => (
        <RunCard key={run.id} run={run} />
      ))}
    </div>
  );
}

interface RunCardProps {
  run: HistoryRun;
}

function RunCard({ run }: RunCardProps) {
  return (
    <Link href={`/runs/${run.id}`} className="block group">
      <Card className="border-zinc-800 bg-zinc-900/50 group-hover:bg-zinc-800/80 transition-colors cursor-pointer">
        <CardContent className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex-shrink-0">
              <RunStatusIcon status={run.status} />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h3 className="font-semibold text-zinc-100 group-hover:text-blue-400 transition-colors">{run.symbol}</h3>
                <RunStatusBadge status={run.status} />
                {run.recommendation && (
                  <span className="sm:hidden text-xs font-semibold px-2 py-0.5 bg-zinc-800 text-zinc-300 rounded">
                    {run.recommendation}
                  </span>
                )}
              </div>
              <p className="text-sm text-zinc-400 mt-1 flex items-center gap-2">
                <span>Trade Date: {run.tradeDate}</span>
                <span>•</span>
                <span>{new Date(run.createdAt).toLocaleString()}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-6">
            {run.recommendation && (
              <div className="text-right hidden sm:block">
                <p className="text-xs text-zinc-500 mb-1">Decision</p>
                <span className="text-sm font-semibold px-2 py-1 bg-zinc-800 rounded text-zinc-300">
                  {run.recommendation}
                </span>
              </div>
            )}
            <ChevronRight className="w-5 h-5 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
