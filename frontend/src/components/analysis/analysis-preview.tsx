import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalysisResponse } from "@/lib/api/types";

interface AnalysisPreviewProps {
  data: AnalysisResponse | undefined;
}

export function AnalysisPreview({ data }: AnalysisPreviewProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-900 text-zinc-50">
      <CardHeader>
        <CardTitle>Analysis Preview</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data ? (
          <>
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              <p className="text-sm font-medium text-blue-400">Analysts</p>
              <div className="mt-2 space-y-3">
                {data.analysts.map((a, i) => (
                  <div key={i} className="space-y-1">
                    <p className="text-xs font-semibold text-zinc-300">
                      {a.analyst}
                    </p>
                    <p className="text-sm text-zinc-400">{a.summary}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              <p className="text-sm font-medium text-emerald-400">
                Decision Advisor
              </p>
              <div className="mt-2 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold px-2 py-1 bg-zinc-800 rounded">
                    {data.decision.recommendation}
                  </span>
                  <span className="text-xs text-zinc-400">
                    Confidence: {(data.decision.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-sm text-zinc-400">
                  {data.decision.reasoning}
                </p>
                {data.decision.riskNotes.length > 0 && (
                  <ul className="list-disc list-inside mt-2 text-xs text-red-400/80">
                    {data.decision.riskNotes.map((note, i) => (
                      <li key={i}>{note}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {data.reflection && (
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                <p className="text-sm font-medium text-purple-400">Reflection</p>
                <div className="mt-2 space-y-2">
                  <p className="text-sm text-zinc-400">
                    <span className="font-semibold text-zinc-300">Guidance: </span>
                    {data.reflection.guidance}
                  </p>
                  {data.reflection.insights.length > 0 && (
                    <ul className="list-disc list-inside text-xs text-zinc-400 mt-2">
                      {data.reflection.insights.map((insight, i) => (
                        <li key={i}>{insight}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              <p className="text-sm font-medium">Market Analyst</p>
              <p className="mt-2 text-sm text-zinc-400">
                Results will appear here after the analysis is completed.
              </p>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              <p className="text-sm font-medium">Decision Advisor</p>
              <p className="mt-2 text-sm text-zinc-400">
                Recommendation, confidence, and risk notes will appear here.
              </p>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              <p className="text-sm font-medium">Reflection</p>
              <p className="mt-2 text-sm text-zinc-400">
                Post-trade learning output will be shown in this area.
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
