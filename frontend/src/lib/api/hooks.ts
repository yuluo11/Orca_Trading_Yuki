import { useMutation } from "@tanstack/react-query";
import { apiClient } from "./client";
import { AnalysisRequest, AnalysisResponse } from "./types";

/**
 * 启动分析的 Mutation Hook
 */
export function useStartAnalysis() {
  return useMutation<AnalysisResponse, Error, AnalysisRequest>({
    mutationFn: (data: AnalysisRequest) => apiClient.startAnalysis(data),
  });
}
