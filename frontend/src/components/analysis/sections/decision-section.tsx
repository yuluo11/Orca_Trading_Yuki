import { DecisionOutput } from "@/lib/api/types";

export function DecisionSection({ decision }: { decision: DecisionOutput }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <p className="text-sm font-medium text-emerald-400">
        Decision Advisor
      </p>
      <div className="mt-2 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold px-2 py-1 bg-zinc-800 rounded">
            {decision.recommendation}
          </span>
          <span className="text-xs text-zinc-400">
            Confidence: {(decision.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <p className="text-sm text-zinc-400">
          {decision.reasoning}
        </p>
        {decision.riskNotes && decision.riskNotes.length > 0 && (
          <ul className="list-disc list-inside mt-2 text-xs text-red-400/80">
            {decision.riskNotes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
