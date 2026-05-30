import { ReflectionOutput } from "@/lib/api/types";

export function ReflectionSection({ reflection }: { reflection: ReflectionOutput | null }) {
  if (!reflection) return null;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <p className="text-sm font-medium text-purple-400">Reflection</p>
      <div className="mt-2 space-y-2">
        <p className="text-sm text-zinc-400">
          <span className="font-semibold text-zinc-300">Guidance: </span>
          {reflection.guidance}
        </p>
        {reflection.insights && reflection.insights.length > 0 && (
          <ul className="list-disc list-inside text-xs text-zinc-400 mt-2">
            {reflection.insights.map((insight, i) => (
              <li key={i}>{insight}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
