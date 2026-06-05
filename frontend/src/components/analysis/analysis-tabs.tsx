"use client";

import { AnalysisTabValue, VALID_ANALYSIS_TABS } from "@/hooks/use-analysis-tab";

interface AnalysisTabsProps {
  currentTab: AnalysisTabValue;
  onTabChange: (tab: AnalysisTabValue) => void;
}

export function AnalysisTabs({ currentTab, onTabChange }: AnalysisTabsProps) {
  return (
    <div className="flex bg-zinc-950 p-1 rounded-md overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] snap-x">
      {VALID_ANALYSIS_TABS.map((t) => (
        <button
          key={t}
          onClick={() => onTabChange(t)}
          className={`snap-start shrink-0 px-3 py-1.5 text-sm font-medium rounded-sm capitalize transition-colors whitespace-nowrap ${
            currentTab === t 
              ? "bg-zinc-800 text-zinc-50 shadow" 
              : "text-zinc-400 hover:text-zinc-200"
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  );
}
