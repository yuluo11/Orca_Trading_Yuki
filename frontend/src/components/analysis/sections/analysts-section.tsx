import { AnalystResult } from "@/lib/api/types";

export function AnalystsSection({ analysts }: { analysts: AnalystResult[] }) {
  if (analysts.length === 0) return null;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <p className="text-sm font-medium text-blue-400">Analysts</p>
      <div className="mt-2 space-y-3">
        {analysts.map((a, i) => (
          <div key={i} className="space-y-1">
            <p className="text-xs font-semibold text-zinc-300">
              {a.analyst}
            </p>
            <p className="text-sm text-zinc-400">{a.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
