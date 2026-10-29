"use client";

import React, { useEffect, useState } from "react";
import { Activity, CheckCircle2, AlertTriangle, Settings, RefreshCw, Cpu } from "lucide-react";
import { ApiHealthResponse } from "@/lib/types";

interface Props {
  apiUrl: string;
  onApiUrlChange: (newUrl: string) => void;
  onHealthUpdate?: (health: ApiHealthResponse | null) => void;
}

export function BackendStatusIndicator({ apiUrl, onApiUrlChange, onHealthUpdate }: Props) {
  const [health, setHealth] = useState<ApiHealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [customUrl, setCustomUrl] = useState(apiUrl);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/health`, { method: "GET" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ApiHealthResponse = await res.json();
      setHealth(data);
      if (onHealthUpdate) onHealthUpdate(data);
    } catch {
      setHealth(null);
      if (onHealthUpdate) onHealthUpdate(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const timer = setInterval(checkHealth, 15000); // Poll every 15s
    return () => clearInterval(timer);
  }, [apiUrl]);

  const handleSaveUrl = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customUrl.trim().replace(/\/+$/, "");
    if (trimmed) {
      onApiUrlChange(trimmed);
      setIsEditing(false);
    }
  };

  const isReady = health?.status === "healthy" && (health?.models_available?.baseline || health?.models_available?.robust_stain_aug);

  return (
    <div className="relative inline-flex items-center">
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200 shadow-sm text-xs">
        {loading ? (
          <span className="flex items-center gap-1.5 text-slate-500">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-slate-400" />
            <span>Connecting...</span>
          </span>
        ) : isReady ? (
          <span className="flex items-center gap-1.5 text-emerald-700 font-medium">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>AI Models Ready</span>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
              {health?.device || "CPU"}
            </span>
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-amber-700 font-medium">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            <span>Inference Backend Offline</span>
          </span>
        )}

        <button
          type="button"
          onClick={() => setIsEditing(!isEditing)}
          className="text-slate-400 hover:text-slate-700 p-0.5 rounded transition"
          title="Configure Backend API URL"
          aria-label="Configure API endpoint"
        >
          <Settings className="w-3.5 h-3.5" />
        </button>
      </div>

      {isEditing && (
        <div className="absolute right-0 top-10 mt-1 w-80 bg-white rounded-xl shadow-xl border border-slate-200 p-4 z-50 text-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-900">Inference Service Endpoint</span>
            <button
              onClick={() => setIsEditing(false)}
              className="text-slate-400 hover:text-slate-600 font-bold"
            >
              ×
            </button>
          </div>
          <p className="text-slate-500 text-[11px] leading-relaxed">
            The frontend connects to the StainShift PyTorch backend to execute inference with actual trained weights.
          </p>
          <form onSubmit={handleSaveUrl} className="space-y-2">
            <label className="block text-[11px] font-semibold text-slate-700">API Base URL</label>
            <input
              type="text"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              placeholder="http://localhost:8000"
              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => {
                  setCustomUrl("http://localhost:8000");
                  onApiUrlChange("http://localhost:8000");
                  setIsEditing(false);
                }}
                className="px-2 py-1 text-[11px] text-slate-500 hover:text-slate-800"
              >
                Reset Default
              </button>
              <button
                type="submit"
                className="px-3 py-1 rounded bg-brand-600 hover:bg-brand-700 text-white font-medium text-[11px] shadow-sm"
              >
                Save & Connect
              </button>
            </div>
          </form>

          {health && (
            <div className="border-t border-slate-100 pt-2 space-y-1 font-mono text-[10px] text-slate-500">
              <div>Version: {health.version}</div>
              <div>Device: {health.device}</div>
              <div>Baseline: {health.models_available.baseline ? "Loaded" : "Unavailable"}</div>
              <div>Robust: {health.models_available.robust_stain_aug ? "Loaded" : "Unavailable"}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
