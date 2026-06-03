import { useState, useMemo } from "react";
import { HistoryRun, StatusFilter, RecommendationFilter } from "@/lib/api/types";

export function useRunsFilters(runs: HistoryRun[] | undefined) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [recommendationFilter, setRecommendationFilter] = useState<RecommendationFilter>("all");

  const handleClearFilters = () => {
    setSearchQuery("");
    setStatusFilter("all");
    setRecommendationFilter("all");
  };

  const filteredRuns = useMemo(() => {
    return runs?.filter((run) => {
      const matchesSearch = run.symbol.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === "all" || run.status === statusFilter;
      const matchesRec = recommendationFilter === "all" || run.recommendation === recommendationFilter;
      return matchesSearch && matchesStatus && matchesRec;
    });
  }, [runs, searchQuery, statusFilter, recommendationFilter]);

  return {
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter,
    recommendationFilter,
    setRecommendationFilter,
    handleClearFilters,
    filteredRuns,
  };
}
