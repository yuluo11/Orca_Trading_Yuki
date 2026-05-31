import { AnalysisRequest, AnalysisResponse, StartAnalysisResponse, HistoryRun, WebPageContextRequest, WebPageContextResponse } from "./types";

export const MOCK_DELAY = 1500;

// 模拟历史任务数据
const MOCK_HISTORY_RUNS: HistoryRun[] = [
  {
    id: "run_001",
    symbol: "NVDA",
    tradeDate: "2024-03-20",
    status: "completed",
    createdAt: "2024-03-20T08:00:00Z",
    recommendation: "BUY"
  },
  {
    id: "run_002",
    symbol: "TSLA",
    tradeDate: "2024-03-19",
    status: "failed",
    createdAt: "2024-03-19T10:30:00Z"
  },
  {
    id: "run_003",
    symbol: "AAPL",
    tradeDate: "2024-03-18",
    status: "completed",
    createdAt: "2024-03-18T14:15:00Z",
    recommendation: "HOLD"
  }
];

export async function mockStartAnalysis(data: AnalysisRequest): Promise<StartAnalysisResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      // 在实际业务中，由于异步生成，这里我们仅仅先生成一个占位记录并返回 runId
      const newId = `run_${String(MOCK_HISTORY_RUNS.length + 1).padStart(3, '0')}_${Date.now().toString().slice(-4)}`;
      MOCK_HISTORY_RUNS.unshift({
        id: newId,
        symbol: data.symbol.toUpperCase(),
        tradeDate: data.tradeDate,
        status: "completed", // 或者 'running' 如果我们需要模拟轮询
        createdAt: new Date().toISOString(),
        recommendation: "HOLD" // 默认占位
      });

      resolve({
        runId: newId
      });
    }, MOCK_DELAY);
  });
}

export async function mockGetHistory(): Promise<HistoryRun[]> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(MOCK_HISTORY_RUNS);
    }, MOCK_DELAY);
  });
}

export async function mockGetRunDetails(id: string): Promise<AnalysisResponse> {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const run = MOCK_HISTORY_RUNS.find((r) => r.id === id);
      if (!run) {
        reject(new Error("Run not found"));
        return;
      }
      
      // 组装一个包含该 run 信息的结果返回
      resolve({
        analysts: [
          {
            analyst: "Market Analyst",
            summary: `Historical market conditions for ${run.symbol} on ${run.tradeDate} indicated a typical pattern.`,
            details: {},
          },
        ],
        decision: {
          recommendation: run.recommendation === "BUY" || run.recommendation === "SELL" || run.recommendation === "HOLD" ? run.recommendation : "HOLD",
          confidence: 0.8,
          reasoning: `Decision made during run ${id} based on snapshot data from ${run.tradeDate}.`,
          riskNotes: ["Past performance is not indicative of future results."],
        },
        reflection: {
          insights: [`Reviewing the outcome for ${run.symbol} shows this was a standard scenario.`],
          guidance: "Evaluate post-trade performance against current market context.",
        },
      });
    }, MOCK_DELAY);
  });
}

export async function mockCollectWebPageContext(
  data: WebPageContextRequest,
): Promise<WebPageContextResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const host = new URL(data.url).host;
      const symbol = data.symbol?.trim().toUpperCase();
      const title = symbol ? `${symbol} URL Context` : "Collected URL Context";
      const extraContext = [
        `[Collected context] ${title} | ${data.url}${symbol ? ` | ${symbol}` : ""} | ${data.category || "web_page"}`,
        `Mock extracted context from ${host}. The page appears relevant to the current analysis and should be reviewed as temporary dynamic context.`,
      ].join("\n");

      resolve({
        mode: data.persist ? "persist" : "context_only",
        persisted: Boolean(data.persist),
        extraContext,
        items: [
          {
            name: `web_${host.replace(/[^a-z0-9]+/gi, "_").toLowerCase()}`,
            text: extraContext,
            metadata: {
              source_url: data.url,
              title,
              category: data.category || "web_page",
              ...(symbol ? { symbol } : {}),
            },
          },
        ],
      });
    }, 600);
  });
}
