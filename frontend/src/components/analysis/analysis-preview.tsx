import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalysisResponse } from "@/lib/api/types";
import { Loader2, AlertCircle, Info, LineChart } from "lucide-react";

interface AnalysisPreviewProps {
  data: AnalysisResponse | undefined;
  isPending: boolean;
  error: Error | null;
}

export function AnalysisPreview({ data, isPending, error }: AnalysisPreviewProps) {
  
  // 渲染不同的状态流
  const renderContent = () => {
    // 1. Error State
    if (error) {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-red-500/80" />
          <div>
            <p className="text-red-400 font-medium">Analysis Failed</p>
            <p className="text-sm text-zinc-500 mt-1">{error.message || "An unexpected error occurred."}</p>
          </div>
        </div>
      );
    }

    // 2. Loading State
    if (isPending) {
      return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-sm text-zinc-400 animate-pulse">Running multi-dimensional analysis...</p>
        </div>
      );
    }

    // 3. Initial State (No Data)
    if (!data) {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-center space-y-4 opacity-70">
          <LineChart className="w-12 h-12 text-zinc-500" />
          <div>
            <p className="font-medium text-zinc-300">Ready for Analysis</p>
            <p className="text-sm text-zinc-500 mt-1">Enter a symbol and context to begin.</p>
          </div>
        </div>
      );
    }

    // 4. Empty State
    const isEmpty = data.analysts.length === 0 && !data.decision;
    if (isEmpty) {
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

    // 5. Success State
    return (
      <div className="grid gap-4 animate-in fade-in duration-500">
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
      </div>
    );
  };

  return (
    <Card className="border-zinc-800 bg-zinc-900 text-zinc-50 flex flex-col h-full">
      <CardHeader className="pb-4">
        <CardTitle>Analysis Preview</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        {renderContent()}
      </CardContent>
    </Card>
  );
}
