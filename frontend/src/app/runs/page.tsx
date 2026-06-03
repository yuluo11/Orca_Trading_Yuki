"use client";

import { useGetHistory } from "@/lib/api/hooks";
import { Card, CardContent } from "@/components/ui/card";
import { Clock } from "lucide-react";
import { RunsList } from "@/components/runs/runs-list";
import { RunsFilters } from "@/components/runs/runs-filters";
import { useRunsFilters } from "@/hooks/use-runs-filters";
import { RunsStats } from "@/components/runs/runs-stats";

export default function RunsPage() {
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
        <div className="flex items-center justify-center h-48">
          <Clock className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      )}

      {error && (
        <Card className="border-red-900 bg-red-950/20 mb-4">
          <CardContent className="pt-6">
            <p className="text-red-400">Failed to load history runs: {error.message}</p>
          </CardContent>
        </Card>
      )}

      {!isLoading && !error && filteredRuns && runs && (
        <RunsList runs={filteredRuns} totalRuns={runs.length} />
      )}
    </main>
  );
}
