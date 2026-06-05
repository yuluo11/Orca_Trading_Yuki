"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalysisResponse } from "@/lib/api/types";

import { ErrorState } from "./states/error-state";
import { LoadingState } from "./states/loading-state";
import { InitialState } from "./states/initial-state";
import { EmptyState } from "./states/empty-state";

import { AnalystsSection } from "./sections/analysts-section";
import { DecisionSection } from "./sections/decision-section";
import { ReflectionSection } from "./sections/reflection-section";

import { AnalysisTabs } from "./analysis-tabs";
import { useAnalysisTab, AnalysisTabValue } from "@/hooks/use-analysis-tab";

interface AnalysisPreviewProps {
  data: AnalysisResponse | undefined;
  isPending: boolean;
  error: Error | null;
  enableTabs?: boolean;
}

export function AnalysisPreview(props: AnalysisPreviewProps) {
  if (props.enableTabs) {
    return <AnalysisPreviewWithTabs {...props} />;
  }
  return <AnalysisPreviewInner {...props} tab="overview" onTabChange={() => {}} />;
}

function AnalysisPreviewWithTabs(props: AnalysisPreviewProps) {
  const { tab, setTab } = useAnalysisTab();
  return <AnalysisPreviewInner {...props} tab={tab} onTabChange={setTab} />;
}

interface InnerProps extends AnalysisPreviewProps {
  tab: AnalysisTabValue;
  onTabChange: (tab: AnalysisTabValue) => void;
}

function AnalysisPreviewInner({ data, isPending, error, enableTabs, tab, onTabChange }: InnerProps) {
  const renderContent = () => {
    if (error) return <ErrorState error={error} />;
    if (isPending) return <LoadingState />;
    if (!data) return <InitialState />;

    const isEmpty = data.analysts.length === 0 && !data.decision;
    if (isEmpty) return <EmptyState />;

    return (
      <div className="grid gap-4 animate-in fade-in duration-500 mt-4">
        {(tab === "overview" || tab === "analysts") && <AnalystsSection analysts={data.analysts} />}
        {(tab === "overview" || tab === "decision") && data.decision && <DecisionSection decision={data.decision} />}
        {(tab === "overview" || tab === "reflection") && <ReflectionSection reflection={data.reflection} />}
      </div>
    );
  };

  return (
    <Card className="border-zinc-800 bg-zinc-900 text-zinc-50 flex flex-col h-full">
      <CardHeader className="pb-4 border-b border-zinc-800">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle>Analysis Preview</CardTitle>
          {enableTabs && (
            <AnalysisTabs currentTab={tab} onTabChange={onTabChange} />
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto pt-4">
        {renderContent()}
      </CardContent>
    </Card>
  );
}
