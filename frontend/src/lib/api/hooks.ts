import { useMutation, useQuery, UseMutationOptions, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import { AnalysisRequest, AnalysisResponse, StartAnalysisResponse, HistoryRun, WebPageContextRequest, WebPageContextResponse } from "./types";

/**
 * 启动分析的 Mutation Hook
 */
export function useStartAnalysis(
  options?: UseMutationOptions<StartAnalysisResponse, Error, AnalysisRequest>
) {
  const queryClient = useQueryClient();
  return useMutation<StartAnalysisResponse, Error, AnalysisRequest>({
    mutationFn: (data: AnalysisRequest) => apiClient.startAnalysis(data),
    ...options,
    onSuccess: (...args) => {
      // 成功后，让历史记录的缓存失效，确保页面切换时重新加载 mock/真实数据
      queryClient.invalidateQueries({ queryKey: ["historyRuns"] });
      if (options?.onSuccess) {
        options.onSuccess(...args);
      }
    },
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
