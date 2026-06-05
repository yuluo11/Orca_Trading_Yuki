import { useSearchParams, useRouter, usePathname } from "next/navigation";

export type AnalysisTabValue = "overview" | "analysts" | "decision" | "reflection";
export const VALID_ANALYSIS_TABS: AnalysisTabValue[] = ["overview", "analysts", "decision", "reflection"];

export function useAnalysisTab() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const currentTab = searchParams.get("tab");
  const tab: AnalysisTabValue = VALID_ANALYSIS_TABS.includes(currentTab as AnalysisTabValue) 
    ? (currentTab as AnalysisTabValue) 
    : "overview";

  const setTab = (newTab: AnalysisTabValue) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", newTab);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  return { tab, setTab };
}
