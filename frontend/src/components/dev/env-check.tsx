"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, USE_MOCK } from "@/lib/api/client";
import { AlertTriangle, Server, Database } from "lucide-react";

export function EnvCheck() {
  const [hostname, setHostname] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setHostname(window.location.hostname);
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  const isRemoteHost =
    hostname !== null && hostname !== "localhost" && hostname !== "127.0.0.1";
  const isApiLocal =
    API_BASE_URL.includes("localhost") || API_BASE_URL.includes("127.0.0.1");
  const isMisconfigured = isRemoteHost && isApiLocal;

  return (
    <>
      {/* 致命配置错误拦截 (Production Misconfig Banner) */}
      {isMisconfigured && (
        <div className="fixed top-0 left-0 right-0 z-[100] bg-red-600 text-white p-3 text-sm flex items-start sm:items-center justify-center shadow-xl border-b border-red-800 animate-in slide-in-from-top">
          <AlertTriangle className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5 sm:mt-0" />
          <div className="flex flex-col sm:flex-row gap-1 sm:gap-4 items-start sm:items-center">
            <span className="font-semibold">Deployment Warning:</span>
            <span>
              You are accessing this app from a remote domain, but NEXT_PUBLIC_API_URL is configured to localhost.
            </span>
            <code className="bg-red-800/50 px-2 py-0.5 rounded text-xs font-mono">
              {API_BASE_URL}
            </code>
          </div>
        </div>
      )}

      {/* 开发环境指示器 (Dev Indicator) */}
      {process.env.NODE_ENV === "development" && (
        <div className="fixed bottom-4 left-4 z-[90] bg-zinc-900/95 border border-zinc-700 rounded-lg shadow-lg p-3 flex flex-col gap-3 backdrop-blur-md text-xs text-zinc-300 max-w-[280px]">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
            <span className="font-semibold text-zinc-100">Environment Config</span>
            <span className="bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded uppercase text-[10px] font-bold">
              {process.env.NODE_ENV}
            </span>
          </div>
          <div className="flex items-start gap-2">
            <Server className="w-4 h-4 text-zinc-500 flex-shrink-0 mt-0.5" />
            <div className="flex flex-col gap-1">
              <span className="text-zinc-500 font-semibold uppercase text-[10px]">API_BASE_URL</span>
              <span className="break-all font-mono text-zinc-200">{API_BASE_URL}</span>
              {isApiLocal && (
                <span className="text-[10px] text-amber-500/90 leading-tight mt-0.5">
                  Local API URL detected. Set a public API URL before deploying.
                </span>
              )}
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Database className={`w-4 h-4 flex-shrink-0 mt-0.5 ${USE_MOCK ? 'text-amber-500' : 'text-green-500'}`} />
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-zinc-500 font-semibold uppercase text-[10px]">USE_MOCK_API</span>
                <strong className={USE_MOCK ? 'text-amber-500' : 'text-green-500'}>{USE_MOCK ? 'ON' : 'OFF'}</strong>
              </div>
              {USE_MOCK && (
                <span className="text-[10px] text-amber-500/90 leading-tight mt-0.5">
                  Mock API is enabled. Disable it before production deployment.
                </span>
              )}
            </div>
          </div>
          <div className="mt-1 pt-2 border-t border-zinc-800/50 flex flex-col gap-1">
            {!isApiLocal && !USE_MOCK ? (
              <span className="text-green-500 font-semibold text-[11px]">Ready for deployment checks.</span>
            ) : (
              <span className="text-amber-500 font-semibold text-[11px]">Production risks detected.</span>
            )}
            <span className="text-[10px] text-zinc-500">
              See <code>frontend/DEPLOYMENT.md</code> for details.
            </span>
          </div>
        </div>
      )}
    </>
  );
}
