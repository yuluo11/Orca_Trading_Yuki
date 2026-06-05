import { useMemo } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { HistoryRun, StatusFilter, RecommendationFilter, SortOption } from "@/lib/api/types";

const ITEMS_PER_PAGE = 10;

const isValidStatus = (val: string | null): val is StatusFilter => 
  ["all", "completed", "failed", "running"].includes(val as string);

const isValidRec = (val: string | null): val is RecommendationFilter => 
  ["all", "BUY", "SELL", "HOLD"].includes(val as string);

const isValidSort = (val: string | null): val is SortOption => 
  ["date-desc", "date-asc", "symbol-asc", "symbol-desc"].includes(val as string);

const parsePage = (val: string | null): number => {
  if (!val || !/^\d+$/.test(val)) return 1;
  const parsed = parseInt(val, 10);
  return parsed < 1 ? 1 : parsed;
};

export function useRunsFilters(runs: HistoryRun[] | undefined) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const searchQuery = searchParams.get("search") || "";
  const statusFilter = isValidStatus(searchParams.get("status")) ? searchParams.get("status") as StatusFilter : "all";
  const recommendationFilter = isValidRec(searchParams.get("rec")) ? searchParams.get("rec") as RecommendationFilter : "all";
  const sortBy = isValidSort(searchParams.get("sort")) ? searchParams.get("sort") as SortOption : "date-desc";
  const rawPage = parsePage(searchParams.get("page"));

  const updateUrl = (updates: Record<string, string | number | null>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (
        value === null || 
        value === "all" || 
        value === "" || 
        (key === "page" && value === 1) || 
        (key === "sort" && value === "date-desc")
      ) {
        params.delete(key);
      } else {
        params.set(key, String(value));
      }
    });
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const handleClearFilters = () => {
    router.replace(pathname, { scroll: false });
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

  const totalPages = Math.max(1, Math.ceil(filteredRuns.length / ITEMS_PER_PAGE));
  const currentPage = Math.min(rawPage, totalPages);

  const paginatedRuns = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredRuns.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredRuns, currentPage]);

  return {
    searchQuery,
    setSearchQuery: (val: string) => updateUrl({ search: val, page: 1 }),
    statusFilter,
    setStatusFilter: (val: StatusFilter) => updateUrl({ status: val, page: 1 }),
    recommendationFilter,
    setRecommendationFilter: (val: RecommendationFilter) => updateUrl({ rec: val, page: 1 }),
    sortBy,
    setSortBy: (val: SortOption) => updateUrl({ sort: val, page: 1 }),
    handleClearFilters,
    filteredRuns,
    paginatedRuns,
    currentPage,
    setCurrentPage: (val: number | ((prev: number) => number)) => {
      const newPage = typeof val === "function" ? val(currentPage) : val;
      updateUrl({ page: newPage });
    },
    totalPages,
  };
}
