import { XCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function FailedRunState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center border border-dashed border-red-900/50 rounded-lg bg-red-950/10">
      <div className="w-16 h-16 mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
        <XCircle className="w-8 h-8 text-red-500" />
      </div>
      <h3 className="text-xl font-semibold text-zinc-200 mb-2">Analysis Run Failed</h3>
      <p className="text-zinc-500 mb-6 max-w-md">
        This analysis task encountered an error during execution and could not be completed. The process might have timed out or failed to gather the necessary data.
      </p>
      <Link href="/">
        <Button variant="outline" className="border-zinc-700 hover:bg-zinc-800">
          Start New Analysis
        </Button>
      </Link>
    </div>
  );
}
