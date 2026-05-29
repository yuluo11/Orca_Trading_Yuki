"use client";

import { useStartAnalysis } from "@/lib/api/hooks";
import { AnalysisForm } from "@/components/analysis/analysis-form";
import { AnalysisPreview } from "@/components/analysis/analysis-preview";

export default function Home() {
  const { mutate: startAnalysis, isPending, data, error } = useStartAnalysis();

  return (
    <main className="grid flex-1 gap-6 lg:grid-cols-[420px_1fr]">
      <AnalysisForm 
        onSubmit={startAnalysis} 
        isPending={isPending} 
        error={error} 
      />
      <AnalysisPreview 
        data={data} 
        isPending={isPending} 
        error={error} 
      />
    </main>
  );
}
