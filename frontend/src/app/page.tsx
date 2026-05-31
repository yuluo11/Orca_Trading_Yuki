"use client";

import { toast } from "sonner";
import { useStartAnalysis } from "@/lib/api/hooks";
import { AnalysisForm } from "@/components/analysis/analysis-form";
import { AnalysisPreview } from "@/components/analysis/analysis-preview";

import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  const { mutate: startAnalysis, isPending, error } = useStartAnalysis({
    onSuccess: (data) => {
      toast.success("Analysis completed successfully!");
      if (data.runId) {
        router.push(`/runs/${data.runId}`);
      }
    }
  });

  return (
    <main className="grid flex-1 gap-6 lg:grid-cols-[420px_1fr]">
      <AnalysisForm 
        onSubmit={startAnalysis} 
        isPending={isPending} 
        error={error} 
      />
      <AnalysisPreview 
        data={undefined} 
        isPending={isPending} 
        error={error} 
      />
    </main>
  );
}
