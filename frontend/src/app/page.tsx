"use client";

import { useStartAnalysis } from "@/lib/api/hooks";
import { AnalysisForm } from "@/components/analysis/analysis-form";
import { AnalysisPreview } from "@/components/analysis/analysis-preview";
import { Header } from "@/components/layout/header";

export default function Home() {
  const { mutate: startAnalysis, isPending, data, error } = useStartAnalysis();

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-6">
        <Header />

        <section className="grid flex-1 gap-6 lg:grid-cols-[420px_1fr]">
          <AnalysisForm 
            onSubmit={startAnalysis} 
            isPending={isPending} 
            error={error} 
          />
          <AnalysisPreview data={data} />
        </section>
      </div>
    </main>
  );
}
