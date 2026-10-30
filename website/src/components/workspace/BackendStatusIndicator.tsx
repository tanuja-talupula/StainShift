"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, Settings, RefreshCw } from "lucide-react";
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

  const isReady =
    health?.status === "healthy" &&
    (health?.models_available?.baseline || health?.models_available?.robust_stain_aug);

  return (
    <div className="relative inline-flex items-center">
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-[#E8E4DD] shadow-sm text-xs">
        {loading ? (
          <span className="flex items-center gap-1.5 text-charcoal-500">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-charcoal-400" />
            <span>Connecting...</span>
          </span>
        ) : isReady ? (
          <span className="flex items-center gap-1.5 text-[#2D5A46] font-medium">
            <span className="w-2 h-2 rounded-full bg-[#2D5A46] inline-block animate-pulse" />
            <span>AI Models Ready</span>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-[#EAF2ED] text-[#244737] border border-[#D5E5DA]">
              {health?.device || "CPU"}
            </span>
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-[#8A532B] font-medium">
            <AlertTriangle className="w-3.5 h-3.5 text-[#8A532B]" />
            <span>Inference Backend Offline</span>
          </span>
        )}

        <button
          type="button"
          onClick={() => setIsEditing(!isEditing)}
          className="text-charcoal-400 hover:text-charcoal-700 p-0.5 rounded-full hover:bg-[#F3EFEA] transition"
          title="Configure Backend API URL"
          aria-label="Configure API endpoint"
        >
          <Settings className="w-3.5 h-3.5" />
        </button>
      </div>

      {isEditing && (
        <div className="absolute right-0 top-10 mt-1 w-84 bg-[#FAF8F5] rounded-2xl shadow-xl border border-[#E8E4DD] p-4 z-50 text-xs space-y-3">
          <div className="flex items-center justify-between border-b border-[#E8E4DD] pb-2">
            <span className="font-serif font-medium text-sm text-charcoal-900">Inference Service Endpoint</span>
            <button
              onClick={() => setIsEditing(false)}
              className="text-charcoal-400 hover:text-charcoal-700 font-bold p-1"
            >
              ×
            </button>
          </div>
          <p className="text-charcoal-500 text-[11px] leading-relaxed">
            The frontend connects to the StainShift PyTorch backend to execute inference with real trained weights.
          </p>
          <form onSubmit={handleSaveUrl} className="space-y-2.5">
            <label className="block text-[11px] font-medium text-charcoal-700">API Base URL</label>
            <input
              type="text"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              placeholder="https://stainshift-api.onrender.com"
              className="w-full px-3 py-1.5 rounded-xl border border-[#DED8CE] bg-white font-mono text-xs focus:outline-none focus:ring-1 focus:ring-[#CC785C]"
            />
            <div className="flex items-center gap-1.5 pt-1">
              <span className="text-[10px] text-charcoal-400 font-medium">Presets:</span>
              <button
                type="button"
                onClick={() => {
                  setCustomUrl("https://stainshift-api.onrender.com");
                  onApiUrlChange("https://stainshift-api.onrender.com");
                  setIsEditing(false);
                }}
                className="px-2.5 py-0.5 rounded-full bg-[#EFECE6] hover:bg-[#E5E0D6] text-charcoal-700 text-[10px] font-medium transition"
              >
                Render Cloud
              </button>
              <button
                type="button"
                onClick={() => {
                  setCustomUrl("http://localhost:8000");
                  onApiUrlChange("http://localhost:8000");
                  setIsEditing(false);
                }}
                className="px-2.5 py-0.5 rounded-full bg-[#EFECE6] hover:bg-[#E5E0D6] text-charcoal-700 text-[10px] font-medium transition"
              >
                Localhost:8000
              </button>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#E8E4DD]">
              <button
                type="button"
                onClick={() => {
                  setCustomUrl("https://stainshift-api.onrender.com");
                  onApiUrlChange("https://stainshift-api.onrender.com");
                  setIsEditing(false);
                }}
                className="px-2.5 py-1 text-[11px] text-charcoal-500 hover:text-charcoal-900"
              >
                Reset Default
              </button>
              <button
                type="submit"
                className="px-3.5 py-1.5 rounded-full bg-charcoal-900 hover:bg-charcoal-800 text-white font-medium text-[11px] shadow-sm transition"
              >
                Save & Connect
              </button>
            </div>
          </form>

          {health && (
            <div className="border-t border-[#E8E4DD] pt-2 space-y-1 font-mono text-[10px] text-charcoal-500">
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
