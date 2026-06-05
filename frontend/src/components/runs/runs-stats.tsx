import { HistoryRun } from "@/lib/api/types";
import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2, XCircle, Clock, Activity } from "lucide-react";

interface RunsStatsProps {
  runs: HistoryRun[];
}

export function RunsStats({ runs }: RunsStatsProps) {
  if (!runs || runs.length === 0) return null;

  const total = runs.length;
  const completed = runs.filter((r) => r.status === "completed").length;
  const running = runs.filter((r) => r.status === "running").length;
  const failed = runs.filter((r) => r.status === "failed").length;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <StatCard 
        title="Total Runs" 
        value={total} 
        icon={<Clock className="h-4 w-4 text-zinc-400" />} 
      />
      <StatCard 
        title="Completed" 
        value={completed} 
        icon={<CheckCircle2 className="h-4 w-4 text-emerald-500" />} 
      />
      <StatCard 
        title="Running" 
        value={running} 
        icon={<Activity className="h-4 w-4 text-blue-500" />} 
      />
      <StatCard 
        title="Failed" 
        value={failed} 
        icon={<XCircle className="h-4 w-4 text-red-500" />} 
      />
    </div>
  );
}

function StatCard({ title, value, icon }: { title: string; value: number; icon: React.ReactNode }) {
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-4 flex flex-col gap-1">
        <div className="flex items-center gap-2 text-zinc-400 text-sm font-medium">
          {icon}
          {title}
        </div>
        <div className="text-2xl font-bold text-zinc-100">
          {value}
        </div>
      </CardContent>
    </Card>
  );
}
