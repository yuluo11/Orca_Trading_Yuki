import { HistoryRun } from "@/lib/api/types";
import { Activity, CheckCircle2, Clock, XCircle } from "lucide-react";

interface RunStatusProps {
  status: HistoryRun["status"];
}

export function RunStatusIcon({ status }: RunStatusProps) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
    case "failed":
      return <XCircle className="w-5 h-5 text-red-500" />;
    case "running":
      return <Clock className="w-5 h-5 text-blue-500 animate-pulse" />;
    default:
      return <Activity className="w-5 h-5 text-zinc-500" />;
  }
}

export function RunStatusBadge({ status }: RunStatusProps) {
  const getStatusClass = (status: HistoryRun["status"]) => {
    switch (status) {
      case "completed":
        return "text-emerald-500 bg-emerald-500/10";
      case "failed":
        return "text-red-500 bg-red-500/10";
      case "running":
        return "text-blue-500 bg-blue-500/10";
      default:
        return "text-zinc-500 bg-zinc-500/10";
    }
  };

  const label = status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getStatusClass(status)}`}>
      {label}
    </span>
  );
}
