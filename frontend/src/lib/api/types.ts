export interface AnalysisRequest {
  symbol: string;
  tradeDate: string;
  context: string;
}

export interface WebPageContextRequest {
  url: string;
  symbol?: string;
  category?: string;
  persist?: boolean;
}

export interface WebPageContextResponse {
  mode: "context_only" | "persist";
  persisted: boolean;
  extraContext: string;
  items: {
    name: string;
    text: string;
    metadata: Record<string, unknown>;
  }[];
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

export interface StartAnalysisResponse {
  runId: string;
}

export interface AnalysisResponse {
  analysts: AnalystResult[];
  decision: DecisionOutput;
  reflection: ReflectionOutput | null;
}

export interface HistoryRun {
  id: string;
  symbol: string;
  tradeDate: string;
  status: "completed" | "failed" | "running";
  createdAt: string;
  recommendation?: string;
}
