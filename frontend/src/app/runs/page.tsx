"use client";

import { Suspense } from "react";
import { useGetHistory } from "@/lib/api/hooks";
import { isBackendUnavailableError, BACKEND_UNAVAILABLE_MESSAGE } from "@/lib/api/errors";
import { Card, CardContent } from "@/components/ui/card";
import { Clock } from "lucide-react";
import { RunsList } from "@/components/runs/runs-list";
import { RunsListSkeleton } from "@/components/runs/runs-list-skeleton";
import { RunsFilters } from "@/components/runs/runs-filters";
import { useRunsFilters } from "@/hooks/use-runs-filters";
import { RunsStats } from "@/components/runs/runs-stats";
import { RunsPagination } from "@/components/runs/runs-pagination";

function RunsPageContent() {
  const { data: runs, isLoading, error } = useGetHistory();
  
  const {
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter,
    recommendationFilter,
    setRecommendationFilter,
    sortBy,
    setSortBy,
    handleClearFilters,
    filteredRuns,
    paginatedRuns,
    currentPage,
    setCurrentPage,
    totalPages,
  } = useRunsFilters(runs);

  return (
    <main className="flex-1 w-full max-w-4xl mx-auto pb-12">
      <div className="mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold flex items-baseline gap-3">
            History Runs
            {runs && (
              <span className="text-sm font-normal text-zinc-500">
                Showing {filteredRuns.length} of {runs.length} runs
              </span>
            )}
          </h2>
          <p className="text-sm text-zinc-400 mt-1">View your previous analysis tasks and their outcomes.</p>
        </div>
        
        <RunsFilters
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          statusFilter={statusFilter}
          onStatusChange={setStatusFilter}
          recommendationFilter={recommendationFilter}
          onRecommendationChange={setRecommendationFilter}
          sortBy={sortBy}
          onSortChange={setSortBy}
          onClear={handleClearFilters}
        />
      </div>

      {!isLoading && !error && runs && (
        <RunsStats runs={runs} />
      )}

      {isLoading && (
        <RunsListSkeleton />
      )}

      {error && (
        <Card className="border-red-900 bg-red-950/20 mb-4">
          <CardContent className="pt-6">
            {isBackendUnavailableError(error) ? (
              <p className="text-red-400">
                {BACKEND_UNAVAILABLE_MESSAGE}
              </p>
            ) : (
              <p className="text-red-400">Failed to load history runs: {error.message}</p>
            )}
          </CardContent>
        </Card>
      )}

      {!isLoading && !error && filteredRuns && runs && (
        <div className="flex flex-col gap-4">
          <RunsList runs={paginatedRuns} totalRuns={runs.length} onClearFilters={handleClearFilters} />
          <RunsPagination 
            currentPage={currentPage}
            totalPages={totalPages}
            setCurrentPage={setCurrentPage}
          />
        </div>
      )}
    </main>
  );
}

export default function RunsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-48">
        <Clock className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    }>
      <RunsPageContent />
    </Suspense>
  );
}
