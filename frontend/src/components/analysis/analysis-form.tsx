import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { toast } from "sonner";
import { Link2, Loader2, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCollectWebPageContext } from "@/lib/api/hooks";
import { AnalysisRequest } from "@/lib/api/types";
import { isBackendUnavailableError, BACKEND_UNAVAILABLE_MESSAGE } from "@/lib/api/errors";

const formSchema = z.object({
  symbol: z.string().min(1, "Symbol is required").toUpperCase(),
  tradeDate: z.string().min(1, "Trade Date is required"),
  context: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

interface AnalysisFormProps {
  onSubmit: (data: AnalysisRequest) => void;
  isPending: boolean;
  error: Error | null;
}

export function AnalysisForm({ onSubmit, isPending, error }: AnalysisFormProps) {
  const [sourceUrl, setSourceUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  
  // 用于收集并在界面上展示已收集的 URL
  const [collectedUrls, setCollectedUrls] = useState<string[]>([]);
  
  const { mutate: collectUrl, isPending: isCollectingUrl } = useCollectWebPageContext();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      symbol: "",
      tradeDate: new Date().toISOString().split("T")[0],
      context: "",
    },
  });

  const handleSubmit = (values: FormValues) => {
    onSubmit({
      symbol: values.symbol.trim(),
      tradeDate: values.tradeDate,
      context: values.context || "",
    });
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
        symbol: form.getValues("symbol") || undefined,
        category: "web_page",
        persist: false,
      },
      {
        onSuccess: (result) => {
          const currentContext = form.getValues("context") || "";
          const spacer = currentContext.trim() ? "\n\n" : "";
          form.setValue("context", `${currentContext}${spacer}${result.extraContext}`);
          
          setCollectedUrls((prev) => [...prev, trimmedUrl]);
          setSourceUrl("");
          toast.success("URL context extracted and added.");
        },
        onError: (err) => {
          setUrlError(err.message);
          toast.error("Failed to extract URL context.");
        },
      },
    );
  };

  const removeCollectedUrl = (urlToRemove: string) => {
    setCollectedUrls((prev) => prev.filter(url => url !== urlToRemove));
    // 界面上移除 tag 可以让用户知道这个源已经被移除，虽然我们不主动清理已追加的 context 文本
  };

  return (
    <Card className="border-zinc-800 bg-zinc-900 text-zinc-50">
      <CardHeader>
        <CardTitle>New Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            
            <FormField
              control={form.control}
              name="symbol"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-zinc-300">Symbol</FormLabel>
                  <FormControl>
                    <Input placeholder="NVDA" {...field} />
                  </FormControl>
                  <FormDescription className="text-zinc-500">
                    The stock ticker symbol to analyze.
                  </FormDescription>
                  <FormMessage className="text-red-400" />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="tradeDate"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-zinc-300">Trade Date</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
                  </FormControl>
                  <FormMessage className="text-red-400" />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="context"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-zinc-300">Context</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Add market context, thesis, or risk notes..."
                      {...field}
                    />
                  </FormControl>
                  <FormDescription className="text-zinc-500">
                    Manual context or insights gathered from URLs.
                  </FormDescription>
                  <FormMessage className="text-red-400" />
                </FormItem>
              )}
            />

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
              
              {collectedUrls.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {collectedUrls.map((url, idx) => (
                    <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-500/10 text-blue-400 text-xs rounded-full border border-blue-500/20">
                      <span className="max-w-[150px] truncate">{new URL(url).hostname}</span>
                      <button 
                        type="button" 
                        onClick={() => removeCollectedUrl(url)}
                        className="hover:text-blue-300"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {error && (
              <div className="text-sm text-red-500 mt-2">
                {isBackendUnavailableError(error) ? (
                  <>
                    <p className="font-medium">{BACKEND_UNAVAILABLE_MESSAGE}</p>
                  </>
                ) : (
                  `Error: ${error.message}`
                )}
              </div>
            )}

            <Button
              type="submit"
              className="w-full mt-4"
              disabled={isPending}
            >
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running Analysis...
                </>
              ) : (
                "Start Analysis"
              )}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
