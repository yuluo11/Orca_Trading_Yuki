"use client";

import { useEffect, useState, useCallback } from "react";
import { API_BASE_URL, USE_MOCK, apiClient } from "@/lib/api/client";
import { Server, Activity, Code2, ShieldAlert, ShieldCheck, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function DiagnosticsPage() {
  const [healthStatus, setHealthStatus] = useState<"pending" | "ok" | "error">("pending");
  const [healthLatency, setHealthLatency] = useState<number | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  const envName = process.env.NODE_ENV || "unknown";

  const waitForMinimumDelay = () =>
    new Promise((resolve) => window.setTimeout(resolve, 600));

  const runHealthCheck = useCallback(async () => {
    setIsChecking(true);

    const start = performance.now();
    let nextStatus: "ok" | "error" = "ok";
    let nextError: string | null = null;

    try {
      await apiClient.checkHealth();
    } catch (err: unknown) {
      nextStatus = "error";
      nextError = err instanceof Error ? err.message : "Unknown connection error";
    }

    await waitForMinimumDelay();

    setHealthLatency(Math.round(performance.now() - start));
    setHealthStatus(nextStatus);
    setHealthError(nextError);
    setIsChecking(false);
  }, []);

  const handleRetry = () => {
    setHealthStatus("pending");
    setHealthLatency(null);
    setHealthError(null);
    void runHealthCheck();
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void runHealthCheck();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [runHealthCheck]);

  const isLocalApi = API_BASE_URL.includes("localhost") || API_BASE_URL.includes("127.0.0.1");
  const isReady = !USE_MOCK && !isLocalApi && healthStatus === "ok" && !isChecking;

  const actionChecklist = [
    {
      id: 'api',
      title: "Configure Public API",
      instruction: "Set NEXT_PUBLIC_API_URL to your deployed backend URL.",
      isResolved: !isLocalApi,
    },
    {
      id: 'mock',
      title: "Disable Mock Mode",
      instruction: "Set NEXT_PUBLIC_USE_MOCK_API=false.",
      isResolved: !USE_MOCK,
    },
    {
      id: 'health',
      title: "Backend Accessibility",
      instruction: "Start backend locally or verify deployed backend health endpoint.",
      isResolved: healthStatus === "ok",
      isPending: isChecking,
    }
  ];

  return (
    <main className="flex-1 space-y-6 pt-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <Activity className="w-8 h-8 text-blue-500" />
          System Diagnostics
        </h1>
        <p className="text-zinc-400">
          Verify your frontend environment and backend connectivity. Useful for post-deployment health checks.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-zinc-800 bg-zinc-900 text-zinc-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code2 className="w-5 h-5 text-zinc-400" />
              Frontend Context
            </CardTitle>
            <CardDescription className="text-zinc-400">
              Current build and rendering configuration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-zinc-800">
              <span className="text-zinc-400">Build Environment</span>
              <span className="font-mono bg-zinc-800 px-2 py-1 rounded text-xs text-zinc-200">
                {envName}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-zinc-800">
              <span className="text-zinc-400">Mock API Mode</span>
              <div className="flex items-center gap-2">
                <span className={`relative flex h-3 w-3`}>
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${USE_MOCK ? 'bg-amber-400' : 'bg-green-400'}`}></span>
                  <span className={`relative inline-flex rounded-full h-3 w-3 ${USE_MOCK ? 'bg-amber-500' : 'bg-green-500'}`}></span>
                </span>
                <span className={`font-semibold ${USE_MOCK ? 'text-amber-500' : 'text-green-500'}`}>
                  {USE_MOCK ? "ON" : "OFF"}
                </span>
              </div>
            </div>
            {USE_MOCK && (
              <div className="bg-amber-500/10 border border-amber-500/20 text-amber-500/90 p-3 rounded-md text-sm mt-4">
                Mock mode is active. No real network requests will be sent to the backend API.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900 text-zinc-50">
          <CardHeader>
            <div className="flex items-center justify-between w-full">
              <CardTitle className="flex items-center gap-2">
                <Server className="w-5 h-5 text-zinc-400" />
                Backend Connectivity
              </CardTitle>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleRetry}
                disabled={isChecking}
                className="h-8 border-zinc-700 text-zinc-300 hover:text-zinc-50 hover:bg-zinc-800"
              >
                <RefreshCw className={`w-3.5 h-3.5 mr-2 ${isChecking ? 'animate-spin' : ''}`} />
                {isChecking ? "Checking..." : "Retry"}
              </Button>
            </div>
            <CardDescription className="text-zinc-400">
              API gateway status and health check
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-zinc-800">
              <span className="text-zinc-400">Configured API Base</span>
              <span className="font-mono bg-zinc-800 px-2 py-1 rounded text-xs text-zinc-200 break-all max-w-[200px] text-right">
                {API_BASE_URL}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-zinc-800">
              <span className="text-zinc-400">Connection Status</span>
              <div className="flex items-center gap-2">
                {isChecking && <span className="text-zinc-500 font-medium">Checking...</span>}
                {!isChecking && healthStatus === "ok" && (
                  <>
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-green-400"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                    <span className="font-semibold text-green-500">Connected</span>
                  </>
                )}
                {!isChecking && healthStatus === "error" && (
                  <>
                    <span className="relative flex h-3 w-3">
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                    </span>
                    <span className="font-semibold text-red-500">Unreachable</span>
                  </>
                )}
              </div>
            </div>
            {healthLatency !== null && (
              <div className="flex justify-between items-center py-2 border-b border-zinc-800">
                <span className="text-zinc-400">Latency</span>
                <span className="text-zinc-300 font-mono text-sm">{healthLatency} ms</span>
              </div>
            )}
            
            {healthStatus === "error" && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-md text-sm mt-4 break-all">
                <strong className="block mb-1">Health Check Failed</strong>
                {healthError}
                <div className="mt-2 text-red-400/80 text-xs">
                  Tip: Verify if the backend server is running and CORS is properly configured for this domain.
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {!isReady ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-500">
              <ShieldAlert className="w-6 h-6" />
              Production Readiness Risk
            </CardTitle>
            <CardDescription className="text-amber-500/80">
              Your environment configuration has potential issues. Please complete the required actions below before deploying.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3">
              {actionChecklist.map(item => (
                <div key={item.id} className="flex items-center justify-between bg-black/20 p-3 rounded-md border border-white/5">
                  <div className="flex items-start gap-3">
                    {item.isPending ? (
                      <RefreshCw className="w-5 h-5 text-zinc-500 animate-spin mt-0.5" />
                    ) : item.isResolved ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />
                    ) : (
                      <XCircle className="w-5 h-5 text-amber-500 mt-0.5" />
                    )}
                    <div className="flex flex-col">
                      <span className="font-medium text-zinc-200">{item.title}</span>
                      <span className="text-sm text-zinc-400">{item.instruction}</span>
                    </div>
                  </div>
                  <div className="hidden sm:block">
                    {item.isPending ? (
                      <span className="px-2 py-1 bg-zinc-800 text-zinc-400 text-xs rounded-full font-medium">Checking</span>
                    ) : item.isResolved ? (
                      <span className="px-2 py-1 bg-green-500/20 text-green-500 text-xs rounded-full font-medium">Resolved</span>
                    ) : (
                      <span className="px-2 py-1 bg-amber-500/20 text-amber-500 text-xs rounded-full font-medium">Required</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="pt-4 flex items-center gap-3">
              <a
                href="https://github.com/yuluo11/Orca_Trading_Yuki/blob/fronted-realization/frontend/DEPLOYMENT.md"
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-9 items-center justify-center rounded-md border border-amber-500/30 px-4 py-2 text-sm font-medium text-amber-500 transition-colors hover:bg-amber-500/10 hover:text-amber-400"
              >
                Open Deployment Guide
              </a>
              <span className="text-xs text-zinc-500">frontend/DEPLOYMENT.md</span>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-green-500/30 bg-green-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-500">
              <ShieldCheck className="w-6 h-6" />
              Ready to Deploy
            </CardTitle>
            <CardDescription className="text-green-500/80">
              All environment configurations look solid. The backend is accessible and production settings are correctly applied.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3">
              {actionChecklist.map(item => (
                <div key={item.id} className="flex items-center justify-between bg-black/20 p-3 rounded-md border border-white/5">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />
                    <div className="flex flex-col">
                      <span className="font-medium text-zinc-200">{item.title}</span>
                      <span className="text-sm text-zinc-400">{item.instruction}</span>
                    </div>
                  </div>
                  <div className="hidden sm:block">
                    <span className="px-2 py-1 bg-green-500/20 text-green-500 text-xs rounded-full font-medium">Resolved</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="pt-4 flex items-center gap-3">
              <a
                href="https://github.com/yuluo11/Orca_Trading_Yuki/blob/fronted-realization/frontend/DEPLOYMENT.md"
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-9 items-center justify-center rounded-md border border-green-500/30 px-4 py-2 text-sm font-medium text-green-500 transition-colors hover:bg-green-500/10 hover:text-green-400"
              >
                Open Deployment Guide
              </a>
              <span className="text-xs text-zinc-500">frontend/DEPLOYMENT.md</span>
            </div>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
