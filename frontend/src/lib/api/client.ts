import { AnalysisRequest, AnalysisResponse, StartAnalysisResponse, HistoryRun, WebPageContextRequest, WebPageContextResponse } from "./types";
import { mockStartAnalysis, mockGetHistory, mockGetRunDetails, mockCollectWebPageContext } from "./mock";
import { apiFetch } from "./fetch";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
// 默认如果环境变量明确开启 mock，或者根本没配置 API URL 时，回退到 mock 模式
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_API === "true" || !process.env.NEXT_PUBLIC_API_URL;

export const apiClient = {
  /**
   * 发起分析请求
   */
  async startAnalysis(data: AnalysisRequest): Promise<StartAnalysisResponse> {
    if (USE_MOCK) {
      return mockStartAnalysis(data);
    }

    return apiFetch<StartAnalysisResponse>(`${API_BASE_URL}/analysis`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /**
   * 获取历史记录
   */
  async getHistoryRuns(): Promise<HistoryRun[]> {
    if (USE_MOCK) {
      return mockGetHistory();
    }

    return apiFetch<HistoryRun[]>(`${API_BASE_URL}/runs`, {
      method: "GET",
    });
  },

  /**
   * 获取单条历史记录详情
   */
  async getRunDetails(id: string): Promise<AnalysisResponse> {
    if (USE_MOCK) {
      return mockGetRunDetails(id);
    }

    return apiFetch<AnalysisResponse>(`${API_BASE_URL}/runs/${id}`, {
      method: "GET",
    });
  },

  /**
   * Collect a single URL as temporary context or dynamic knowledge.
   */
  async collectWebPageContext(data: WebPageContextRequest): Promise<WebPageContextResponse> {
    if (USE_MOCK) {
      return mockCollectWebPageContext(data);
    }

    return apiFetch<WebPageContextResponse>(`${API_BASE_URL}/knowledge/web-page`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
};
