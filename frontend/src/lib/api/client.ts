import { AnalysisRequest, AnalysisResponse, StartAnalysisResponse, HistoryRun, WebPageContextRequest, WebPageContextResponse } from "./types";
import { mockStartAnalysis, mockGetHistory, mockGetRunDetails, mockCollectWebPageContext } from "./mock";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
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

    // 真实的 API 网络请求逻辑
    const response = await fetch(`${API_BASE_URL}/analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * 获取历史记录
   */
  async getHistoryRuns(): Promise<HistoryRun[]> {
    if (USE_MOCK) {
      return mockGetHistory();
    }

    // 这里可以填写真实的获取历史记录 API
    const response = await fetch(`${API_BASE_URL}/runs`, {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * 获取单条历史记录详情
   */
  async getRunDetails(id: string): Promise<AnalysisResponse> {
    if (USE_MOCK) {
      return mockGetRunDetails(id);
    }

    const response = await fetch(`${API_BASE_URL}/runs/${id}`, {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Collect a single URL as temporary context or dynamic knowledge.
   */
  async collectWebPageContext(data: WebPageContextRequest): Promise<WebPageContextResponse> {
    if (USE_MOCK) {
      return mockCollectWebPageContext(data);
    }

    const response = await fetch(`${API_BASE_URL}/knowledge/web-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }
};
