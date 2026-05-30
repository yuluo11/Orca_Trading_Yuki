import { HistoryRun } from "@/lib/api/types";
import { RunStatusBadge, RunStatusIcon } from "./run-status-badge";

interface RunSummaryProps {
  id: string;
  run?: HistoryRun;
}

export function RunSummary({ id, run }: RunSummaryProps) {
  if (!run) {
    return (
      <div>
        <h2 className="text-2xl font-semibold">Run Details</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Review the complete analysis output for run <code className="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">{id}</code>
        </p>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
      <div>
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-semibold">{run.symbol} Analysis</h2>
          <RunStatusBadge status={run.status} />
          {run.recommendation && (
            <span className="text-xs font-semibold px-2 py-1 bg-zinc-800 text-zinc-300 rounded">
              Decision: {run.recommendation}
            </span>
          )}
        </div>
        <p className="text-sm text-zinc-400 mt-2 flex items-center gap-2">
          <span>Run ID: <code className="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">{id}</code></span>
          <span>•</span>
          <span>Trade Date: {run.tradeDate}</span>
          <span>•</span>
          <span>{new Date(run.createdAt).toLocaleString()}</span>
        </p>
      </div>
      <div className="flex-shrink-0">
        <RunStatusIcon status={run.status} />
      </div>
    </div>
  );
}
