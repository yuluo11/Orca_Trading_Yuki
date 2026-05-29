"use client";

import { useGetHistory } from "@/lib/api/hooks";
import { Card, CardContent } from "@/components/ui/card";
import { Clock } from "lucide-react";
import { RunsList } from "@/components/runs/runs-list";

export default function RunsPage() {
  const { data: runs, isLoading, error } = useGetHistory();

  return (
    <main className="flex-1 w-full max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold">History Runs</h2>
        <p className="text-sm text-zinc-400 mt-1">View your previous analysis tasks and their outcomes.</p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-48">
          <Clock className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      )}

      {error && (
        <Card className="border-red-900 bg-red-950/20">
          <CardContent className="pt-6">
            <p className="text-red-400">Failed to load history runs: {error.message}</p>
          </CardContent>
        </Card>
      )}

      {runs && <RunsList runs={runs} />}
    </main>
  );
}
