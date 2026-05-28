import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { AnalysisRequest } from "@/lib/api/types";

interface AnalysisFormProps {
  onSubmit: (data: AnalysisRequest) => void;
  isPending: boolean;
  error: Error | null;
}

export function AnalysisForm({ onSubmit, isPending, error }: AnalysisFormProps) {
  const [symbol, setSymbol] = useState("");
  // 默认设置为今天
  const [tradeDate, setTradeDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [context, setContext] = useState("");

  const trimmedSymbol = symbol.trim();
  const isValid = trimmedSymbol.length > 0;

  const handleSubmit = () => {
    if (!isValid) return;
    onSubmit({ symbol: trimmedSymbol, tradeDate, context });
  };

  return (
    <Card className="border-zinc-800 bg-zinc-900 text-zinc-50">
      <CardHeader>
        <CardTitle>New Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm text-zinc-300">Symbol</label>
          <Input
            placeholder="NVDA"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm text-zinc-300">Trade Date</label>
          <Input
            type="date"
            value={tradeDate}
            onChange={(e) => setTradeDate(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm text-zinc-300">Context</label>
          <Textarea
            placeholder="Add market context, thesis, or risk notes..."
            value={context}
            onChange={(e) => setContext(e.target.value)}
          />
        </div>

        {error && (
          <div className="text-sm text-red-500">Error: {error.message}</div>
        )}

        <Button
          className="w-full"
          onClick={handleSubmit}
          disabled={isPending || !isValid}
        >
          {isPending ? "Analyzing..." : "Start Analysis"}
        </Button>
      </CardContent>
    </Card>
  );
}
