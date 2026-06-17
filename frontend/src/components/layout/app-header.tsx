"use client";

import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Activity, LayoutDashboard, Stethoscope } from "lucide-react";
import { usePathname } from "next/navigation";

export function AppHeader() {
  const pathname = usePathname();
  const isWorkbench = pathname === "/";
  const isRuns = pathname.startsWith("/runs");
  const isDiagnostics = pathname === "/diagnostics";

  return (
    <header className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-6">
      <div className="flex items-center gap-8">
        <div>
          <p className="text-sm text-zinc-400">Trading Intelligence</p>
          <h1 className="text-2xl font-semibold text-zinc-50">Orca Trading Yuki</h1>
        </div>
        <nav className="flex items-center gap-2 text-sm mt-1">
          <Link 
            href="/" 
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-all ${
              isWorkbench 
                ? "bg-zinc-800 text-zinc-50 font-medium shadow-sm" 
                : "text-zinc-400 hover:text-zinc-50 hover:bg-zinc-800/50"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            Workbench
          </Link>
          <Link 
            href="/runs" 
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-all ${
              isRuns 
                ? "bg-zinc-800 text-zinc-50 font-medium shadow-sm" 
                : "text-zinc-400 hover:text-zinc-50 hover:bg-zinc-800/50"
            }`}
          >
            <Activity className="w-4 h-4" />
            Runs
          </Link>
          <Link 
            href="/diagnostics" 
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md transition-all ${
              isDiagnostics 
                ? "bg-zinc-800 text-zinc-50 font-medium shadow-sm" 
                : "text-zinc-400 hover:text-zinc-50 hover:bg-zinc-800/50"
            }`}
          >
            <Stethoscope className="w-4 h-4" />
            Diagnostics
          </Link>
        </nav>
      </div>
      <Button variant="outline" className="border-zinc-700 text-zinc-300 hover:text-zinc-50 hover:bg-zinc-800">
        Frontend Ready
      </Button>
    </header>
  );
}
