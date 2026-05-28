export interface AnalysisRequest {
  symbol: string;
  tradeDate: string;
  context: string;
}

export interface AnalystResult {
  analyst: string;
  summary: string;
  details: Record<string, unknown>;
}

export interface DecisionOutput {
  recommendation: "BUY" | "SELL" | "HOLD";
  confidence: number;
  reasoning: string;
  riskNotes: string[];
}

export interface ReflectionOutput {
  insights: string[];
  guidance: string;
}

export interface AnalysisResponse {
  analysts: AnalystResult[];
  decision: DecisionOutput;
  reflection: ReflectionOutput | null;
}
