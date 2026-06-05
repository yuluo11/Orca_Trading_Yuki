import { HistoryRun } from "@/lib/api/types";
import { RunStatusBadge, RunStatusIcon } from "./run-status-badge";
import { RunActions } from "./run-actions";

interface RunSummaryProps {
  id: string;
  run?: HistoryRun;
  isFetching: boolean;
  onRefresh: () => Promise<void>;
  isHistoryPending?: boolean;
}

export function RunSummary({ id, run, isFetching, onRefresh, isHistoryPending }: RunSummaryProps) {
  if (isHistoryPending) {
    return (
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-zinc-800 pb-4 animate-pulse gap-4">
        <div>
          <div className="h-8 bg-zinc-800 rounded w-48 mb-2"></div>
          <div className="h-4 bg-zinc-800 rounded w-64 mt-3"></div>
        </div>
        <div className="flex flex-wrap gap-4 self-start md:self-auto">
          <div className="h-9 bg-zinc-800 rounded w-24"></div>
          <div className="h-9 bg-zinc-800 rounded w-8"></div>
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div>
        <h2 className="text-2xl font-semibold text-red-400">Run Not Found</h2>
        <p className="text-sm text-zinc-400 mt-1">
          The requested run <code className="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">{id}</code> could not be found or has been deleted.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-zinc-800 pb-4 gap-4">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-2xl font-semibold">{run.symbol} Analysis</h2>
          <RunStatusBadge status={run.status} />
          {run.recommendation && (
            <span className="text-xs font-semibold px-2 py-1 bg-zinc-800 text-zinc-300 rounded">
              Decision: {run.recommendation}
            </span>
          )}
        </div>
        <p className="text-sm text-zinc-400 mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
          <span>Run ID: <code className="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">{id}</code></span>
          <span>•</span>
          <span>Trade Date: {run.tradeDate}</span>
          <span>•</span>
          <span>{new Date(run.createdAt).toLocaleString()}</span>
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-4 flex-shrink-0 self-start md:self-auto">
        <RunActions id={id} isFetching={isFetching} onRefresh={onRefresh} />
        <RunStatusIcon status={run.status} />
      </div>
    </div>
  );
}
