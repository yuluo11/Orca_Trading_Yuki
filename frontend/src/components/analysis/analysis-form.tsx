import { useState } from "react";
import { Link2, Loader2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useCollectWebPageContext } from "@/lib/api/hooks";
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
  const [sourceUrl, setSourceUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const { mutate: collectUrl, isPending: isCollectingUrl } = useCollectWebPageContext();

  const trimmedSymbol = symbol.trim();
  const isValid = trimmedSymbol.length > 0;

  const handleSubmit = () => {
    if (!isValid) return;
    onSubmit({ symbol: trimmedSymbol, tradeDate, context });
  };

  const handleCollectUrl = () => {
    const trimmedUrl = sourceUrl.trim();
    if (!trimmedUrl) return;

    try {
      new URL(trimmedUrl);
    } catch {
      setUrlError("Enter a valid URL.");
      return;
    }

    setUrlError(null);
    collectUrl(
      {
        url: trimmedUrl,
        symbol: trimmedSymbol || undefined,
        category: "web_page",
        persist: false,
      },
      {
        onSuccess: (result) => {
          setContext((current) => {
            const spacer = current.trim() ? "\n\n" : "";
            return `${current}${spacer}${result.extraContext}`;
          });
          setSourceUrl("");
        },
        onError: (err) => {
          setUrlError(err.message);
        },
      },
    );
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

        <div className="space-y-2 rounded-lg border border-zinc-800 bg-zinc-950/70 p-3">
          <div className="flex items-center gap-2 text-sm text-zinc-300">
            <Link2 className="h-4 w-4 text-blue-400" />
            <span>URL Context</span>
          </div>
          <div className="flex gap-2">
            <Input
              type="url"
              placeholder="https://example.com/market-update"
              value={sourceUrl}
              onChange={(e) => {
                setSourceUrl(e.target.value);
                if (urlError) setUrlError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleCollectUrl();
                }
              }}
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleCollectUrl}
              disabled={isCollectingUrl || !sourceUrl.trim()}
              aria-label="Add URL context"
              title="Add URL context"
            >
              {isCollectingUrl ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
            </Button>
          </div>
          {urlError && <p className="text-xs text-red-400">{urlError}</p>}
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
