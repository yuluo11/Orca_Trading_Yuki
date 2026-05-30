import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalysisResponse } from "@/lib/api/types";

import { ErrorState } from "./states/error-state";
import { LoadingState } from "./states/loading-state";
import { InitialState } from "./states/initial-state";
import { EmptyState } from "./states/empty-state";

import { AnalystsSection } from "./sections/analysts-section";
import { DecisionSection } from "./sections/decision-section";
import { ReflectionSection } from "./sections/reflection-section";

interface AnalysisPreviewProps {
  data: AnalysisResponse | undefined;
  isPending: boolean;
  error: Error | null;
}

export function AnalysisPreview({ data, isPending, error }: AnalysisPreviewProps) {
  const renderContent = () => {
    if (error) return <ErrorState error={error} />;
    if (isPending) return <LoadingState />;
    if (!data) return <InitialState />;

    const isEmpty = data.analysts.length === 0 && !data.decision;
    if (isEmpty) return <EmptyState />;

    return (
      <div className="grid gap-4 animate-in fade-in duration-500">
        <AnalystsSection analysts={data.analysts} />
        {data.decision && <DecisionSection decision={data.decision} />}
        <ReflectionSection reflection={data.reflection} />
      </div>
    );
  };

  return (
    <Card className="border-zinc-800 bg-zinc-900 text-zinc-50 flex flex-col h-full">
      <CardHeader className="pb-4">
        <CardTitle>Analysis Preview</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        {renderContent()}
      </CardContent>
    </Card>
  );
}
