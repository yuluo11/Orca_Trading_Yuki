import { AnalysisRequest, AnalysisResponse } from "./types";

export const MOCK_DELAY = 1500;

export async function mockStartAnalysis(data: AnalysisRequest): Promise<AnalysisResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        analysts: [
          {
            analyst: "Market Analyst",
            summary: `Market conditions for ${data.symbol || "the asset"} are showing a neutral trend.`,
            details: {},
          },
          {
            analyst: "News Analyst",
            summary: "No significant breaking news detected in the last 24 hours.",
            details: {},
          }
        ],
        decision: {
          recommendation: "HOLD",
          confidence: 0.65,
          reasoning: "Insufficient directional momentum and mixed signals across analytical dimensions.",
          riskNotes: [
            "Macro environment remains highly uncertain.",
            "Wait for a clearer breakout signal."
          ],
        },
        reflection: {
          insights: ["Historical backtests indicate whipsaw risks in similar low-volatility regimes."],
          guidance: "Prioritize capital preservation. Do not force trades in choppy markets.",
        },
      });
    }, MOCK_DELAY);
  });
}
