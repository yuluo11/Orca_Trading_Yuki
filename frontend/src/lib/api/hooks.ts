import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import { AnalysisRequest, AnalysisResponse, HistoryRun, WebPageContextRequest, WebPageContextResponse } from "./types";

/**
 * 启动分析的 Mutation Hook
 */
export function useStartAnalysis() {
  return useMutation<AnalysisResponse, Error, AnalysisRequest>({
    mutationFn: (data: AnalysisRequest) => apiClient.startAnalysis(data),
  });
}

/**
 * 获取历史记录的 Query Hook
 */
export function useGetHistory() {
  return useQuery<HistoryRun[], Error>({
    queryKey: ["historyRuns"],
    queryFn: () => apiClient.getHistoryRuns(),
  });
}

/**
 * 获取单条历史记录详情的 Query Hook
 */
export function useGetRunDetails(id: string) {
  return useQuery<AnalysisResponse, Error>({
    queryKey: ["runDetails", id],
    queryFn: () => apiClient.getRunDetails(id),
    enabled: !!id,
  });
}

/**
 * Collect URL content for the current analysis context.
 */
export function useCollectWebPageContext() {
  return useMutation<WebPageContextResponse, Error, WebPageContextRequest>({
    mutationFn: (data: WebPageContextRequest) => apiClient.collectWebPageContext(data),
  });
}
