import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Activity, LayoutDashboard } from "lucide-react";

export function AppHeader() {
  return (
    <header className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-6">
      <div className="flex items-center gap-8">
        <div>
          <p className="text-sm text-zinc-400">Trading Intelligence</p>
          <h1 className="text-2xl font-semibold text-zinc-50">Orca Trading Yuki</h1>
        </div>
        <nav className="flex items-center gap-4 text-sm mt-1">
          <Link 
            href="/" 
            className="flex items-center gap-2 text-zinc-400 hover:text-zinc-50 transition-colors"
          >
            <LayoutDashboard className="w-4 h-4" />
            Workbench
          </Link>
          <Link 
            href="/runs" 
            className="flex items-center gap-2 text-zinc-400 hover:text-zinc-50 transition-colors"
          >
            <Activity className="w-4 h-4" />
            Runs
          </Link>
        </nav>
      </div>
      <Button variant="outline" className="border-zinc-700 text-zinc-300 hover:text-zinc-50 hover:bg-zinc-800">
        Frontend Ready
      </Button>
    </header>
  );
}
