import { Button } from "@/components/ui/button";

interface RunsPaginationProps {
  currentPage: number;
  totalPages: number;
  setCurrentPage: (page: number | ((prev: number) => number)) => void;
}

export function RunsPagination({ currentPage, totalPages, setCurrentPage }: RunsPaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between border-t border-zinc-800 pt-4 mt-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
        disabled={currentPage === 1}
        className="border-zinc-800 bg-transparent hover:bg-zinc-800 text-zinc-300"
      >
        Previous
      </Button>
      <div className="text-sm text-zinc-400">
        Page {currentPage} of {totalPages}
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
        disabled={currentPage === totalPages}
        className="border-zinc-800 bg-transparent hover:bg-zinc-800 text-zinc-300"
      >
        Next
      </Button>
    </div>
  );
}
