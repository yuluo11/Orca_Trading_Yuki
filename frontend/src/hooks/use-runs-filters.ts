import { useState, useMemo } from "react";
import { HistoryRun, StatusFilter, RecommendationFilter, SortOption } from "@/lib/api/types";

export function useRunsFilters(runs: HistoryRun[] | undefined) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [recommendationFilter, setRecommendationFilter] = useState<RecommendationFilter>("all");
  const [sortBy, setSortBy] = useState<SortOption>("date-desc");

  const handleClearFilters = () => {
    setSearchQuery("");
    setStatusFilter("all");
    setRecommendationFilter("all");
    setSortBy("date-desc");
  };

  const filteredRuns = useMemo(() => {
    const filtered = runs?.filter((run) => {
      const matchesSearch = run.symbol.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === "all" || run.status === statusFilter;
      const matchesRec = recommendationFilter === "all" || run.recommendation === recommendationFilter;
      return matchesSearch && matchesStatus && matchesRec;
    });

    if (!filtered) return [];

    return [...filtered].sort((a, b) => {
      switch (sortBy) {
        case "date-asc":
          return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        case "date-desc":
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case "symbol-asc":
          return a.symbol.localeCompare(b.symbol);
        case "symbol-desc":
          return b.symbol.localeCompare(a.symbol);
        default:
          return 0;
      }
    });
  }, [runs, searchQuery, statusFilter, recommendationFilter, sortBy]);

  return {
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
  };
}
