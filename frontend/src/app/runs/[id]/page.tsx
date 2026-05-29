"use client";

import { useGetRunDetails } from "@/lib/api/hooks";
import { AnalysisPreview } from "@/components/analysis/analysis-preview";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { use } from "react";

export default function RunDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const id = resolvedParams.id;
  const { data, isPending, error } = useGetRunDetails(id);

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
        <h2 className="text-2xl font-semibold">Run Details</h2>
        <p className="text-sm text-zinc-400 mt-1">Review the complete analysis output for run <code className="bg-zinc-800 px-1 py-0.5 rounded text-zinc-300">{id}</code></p>
      </div>

      <div className="flex-1 min-h-[500px]">
        <AnalysisPreview 
          data={data}
          isPending={isPending}
          error={error}
        />
      </div>
    </main>
  );
}
