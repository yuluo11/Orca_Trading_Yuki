import { Input } from "@/components/ui/input";
import { Search, X } from "lucide-react";
import { StatusFilter, RecommendationFilter, SortOption } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
const STATUS_FILTERS: StatusFilter[] = ["all", "completed", "failed", "running"];
const REC_FILTERS: RecommendationFilter[] = ["all", "BUY", "SELL", "HOLD"];

interface RunsFiltersProps {
  searchQuery: string;
  onSearchChange: (val: string) => void;
  statusFilter: StatusFilter;
  onStatusChange: (status: StatusFilter) => void;
  recommendationFilter: RecommendationFilter;
  onRecommendationChange: (rec: RecommendationFilter) => void;
  sortBy: SortOption;
  onSortChange: (sort: SortOption) => void;
  onClear: () => void;
}

export function RunsFilters({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusChange,
  recommendationFilter,
  onRecommendationChange,
  sortBy,
  onSortChange,
  onClear,
}: RunsFiltersProps) {
  const hasFilters = searchQuery !== "" || statusFilter !== "all" || recommendationFilter !== "all" || sortBy !== "date-desc";

  return (
    <div className="flex flex-col sm:flex-row flex-wrap items-start sm:items-center gap-3 w-full">
      <div className="relative w-full sm:w-64">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
        <Input
          placeholder="Search by symbol..."
          className="pl-9 h-9 border-zinc-800 bg-zinc-900/50 focus-visible:ring-zinc-700"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>
      
      <div className="flex flex-wrap bg-zinc-900/50 border border-zinc-800 rounded-md p-1 gap-1">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            onClick={() => onStatusChange(status)}
            className={`px-3 py-1 text-xs font-medium rounded capitalize transition-colors ${
              statusFilter === status
                ? "bg-zinc-800 text-zinc-100 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap bg-zinc-900/50 border border-zinc-800 rounded-md p-1 gap-1">
        {REC_FILTERS.map((rec) => (
          <button
            key={rec}
            onClick={() => onRecommendationChange(rec)}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
              recommendationFilter === rec
                ? "bg-zinc-800 text-zinc-100 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {rec === "all" ? "All Recs" : rec}
          </button>
        ))}
      </div>

      <div className="flex items-center bg-zinc-900/50 border border-zinc-800 rounded-md px-1">
        <select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          className="h-8 bg-transparent text-xs text-zinc-300 focus:outline-none cursor-pointer"
        >
          <option value="date-desc">Newest First</option>
          <option value="date-asc">Oldest First</option>
          <option value="symbol-asc">Symbol (A-Z)</option>
          <option value="symbol-desc">Symbol (Z-A)</option>
        </select>
      </div>

      {hasFilters && (
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={onClear}
          className="text-zinc-400 hover:text-zinc-100 px-2 h-8"
        >
          <X className="h-4 w-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}
