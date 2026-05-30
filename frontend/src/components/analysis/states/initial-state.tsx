import { LineChart } from "lucide-react";

export function InitialState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center space-y-4 opacity-70">
      <LineChart className="w-12 h-12 text-zinc-500" />
      <div>
        <p className="font-medium text-zinc-300">Ready for Analysis</p>
        <p className="text-sm text-zinc-500 mt-1">Enter a symbol and context to begin.</p>
      </div>
    </div>
  );
}
