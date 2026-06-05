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

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(id);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      toast.error("Failed to copy Run ID");
    }
  };

  const handleRefresh = async () => {
    try {
      await onRefresh();
      toast.success("Refreshed successfully");
    } catch {
      toast.error("Failed to refresh");
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button 
        variant="outline" 
        size="sm" 
        onClick={handleRefresh}
        disabled={isFetching}
      >
        <RefreshCw className={`w-4 h-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
        Refresh
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
