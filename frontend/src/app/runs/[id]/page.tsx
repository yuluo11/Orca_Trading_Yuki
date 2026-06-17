"use client";

import { useGetRunDetails, useGetHistory } from "@/lib/api/hooks";
import { AnalysisPreview } from "@/components/analysis/analysis-preview";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { use, Suspense } from "react";
import { RunSummary } from "@/components/runs/run-summary";

export default function RunDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const id = resolvedParams.id;
  const { data: detailsData, isPending: isDetailsPending, error: detailsError, refetch, isFetching } = useGetRunDetails(id);
  const { data: historyData, isPending: isHistoryPending } = useGetHistory();

  const currentRun = historyData?.find((run) => run.id === id);

  const handleRefresh = async () => {
    const result = await refetch();

    if (result.error) {
      throw result.error;
    }
  };

  return (
    <main className="flex-1 w-full max-w-4xl mx-auto flex flex-col">
      <div className="mb-6">
        <Link 
          href="/runs" 
          className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-50 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Runs
        </Link>

        <RunSummary id={id} run={currentRun} isFetching={isFetching} onRefresh={handleRefresh} isHistoryPending={isHistoryPending} />
      </div>

      <div className="flex-1 min-h-[500px] mt-4">
        <Suspense fallback={<div className="flex-1 min-h-[500px] bg-zinc-900 border border-zinc-800 rounded-xl animate-pulse"></div>}>
          <AnalysisPreview 
            data={detailsData}
            isPending={isDetailsPending}
            error={detailsError}
            enableTabs
            runStatus={currentRun?.status}
          />
        </Suspense>
      </div>
    </main>
  );
}
