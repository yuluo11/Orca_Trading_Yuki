import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw, Copy, Check } from "lucide-react";
import { toast } from "sonner";

interface RunActionsProps {
  id: string;
  isFetching: boolean;
  onRefresh: () => Promise<void>;
}

export function RunActions({ id, isFetching, onRefresh }: RunActionsProps) {
  const [isCopied, setIsCopied] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const isWorking = isFetching || isRefreshing;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(id);
      setIsCopied(true);
      toast.success("Run ID copied to clipboard");
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      toast.error("Failed to copy automatically", {
        description: (
          <div className="mt-2 flex flex-col gap-1">
            <span className="text-xs text-zinc-400">Please copy manually:</span>
            <code className="bg-zinc-900 text-zinc-200 px-2 py-1 rounded select-all font-mono text-xs break-all border border-zinc-800">
              {id}
            </code>
          </div>
        ),
        duration: 8000,
      });
    }
  };

  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);
      await onRefresh();
      toast.success("Refreshed successfully");
    } catch {
      toast.error("Failed to refresh");
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button 
        variant="outline" 
        size="sm" 
        onClick={handleRefresh}
        disabled={isWorking}
      >
        <RefreshCw className={`w-4 h-4 mr-2 ${isWorking ? 'animate-spin' : ''}`} />
        {isWorking ? "Refreshing..." : "Refresh"}
      </Button>
      <Button variant="outline" size="sm" onClick={handleCopy}>
        {isCopied ? (
          <Check className="w-4 h-4 mr-2 text-green-500" />
        ) : (
          <Copy className="w-4 h-4 mr-2" />
        )}
        {isCopied ? "Copied" : "Copy Run ID"}
      </Button>
    </div>
  );
}
