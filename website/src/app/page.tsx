"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Play,
  RefreshCw,
  Sparkles,
  BarChart2,
  Eye,
  ArrowRight,
  Database,
} from "lucide-react";
import { BackendStatusIndicator } from "@/components/workspace/BackendStatusIndicator";
import { ModelSelector } from "@/components/workspace/ModelSelector";
import { StainControls } from "@/components/workspace/StainControls";
import { ImageUploader } from "@/components/workspace/ImageUploader";
import { PredictionResultView } from "@/components/workspace/PredictionResultView";
import { BatchResultsTable } from "@/components/workspace/BatchResultsTable";
import {
  ApiHealthResponse,
  BatchSummary,
  ImageInferenceResult,
  PredictResponse,
  QueueFileItem,
} from "@/lib/types";

const DEFAULT_API_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://stainshift-api.onrender.com";

export default function WorkspacePage() {
  const [apiUrl, setApiUrl] = useState<string>(DEFAULT_API_URL);
  const [backendHealth, setBackendHealth] = useState<ApiHealthResponse | null>(null);

  // Configuration state
  const [selectedModel, setSelectedModel] = useState<"baseline" | "robust_stain_aug" | "compare">("robust_stain_aug");
  const [selectedCondition, setSelectedCondition] = useState<string>("original");
  const [intensity, setIntensity] = useState<number>(1.0);

  // Queue and results state
  const [queue, setQueue] = useState<QueueFileItem[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [progressText, setProgressText] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [results, setResults] = useState<ImageInferenceResult[]>([]);
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [activeResult, setActiveResult] = useState<ImageInferenceResult | null>(null);

  // File queue management
  const handleAddFiles = (files: File[]) => {
    setErrorMessage(null);
    const newItems: QueueFileItem[] = files.map((file) => {
      const isImage = file.type.startsWith("image/") || /\.(png|jpe?g|tiff?)$/i.test(file.name);
      return {
        id: `${file.name}-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        file,
        previewUrl: isImage ? URL.createObjectURL(file) : "",
        name: file.name,
        size: file.size,
        type: file.type,
        status: "pending",
      };
    });
    setQueue((prev) => [...prev, ...newItems]);
  };

  const handleRemoveFile = (id: string) => {
    setQueue((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return prev.filter((item) => item.id !== id);
    });
  };

  const handleClearQueue = () => {
    queue.forEach((item) => {
      if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
    });
    setQueue([]);
    setErrorMessage(null);
  };

  const handleClearResults = () => {
    setResults([]);
    setSummary(null);
    setActiveResult(null);
    setErrorMessage(null);
  };

  // Inference Execution
  const handleRunPrediction = async () => {
    if (queue.length === 0) {
      setErrorMessage("Please select at least one image or ZIP file to run inference.");
      return;
    }

    setIsRunning(true);
    setErrorMessage(null);
    setProgressText(`Sending ${queue.length} file(s) to inference backend...`);

    // Mark items as processing
    setQueue((prev) => prev.map((item) => ({ ...item, status: "processing" })));

    const formData = new FormData();
    queue.forEach((item) => {
      formData.append("files", item.file, item.name);
    });
    formData.append("model_id", selectedModel);
    formData.append("condition", selectedCondition);
    formData.append("intensity", intensity.toString());

    try {
      const res = await fetch(`${apiUrl}/predict`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server responded with HTTP ${res.status}`);
      }

      const data: PredictResponse = await res.json();

      setResults(data.results);
      setSummary(data.summary);

      // Select first successful result for view
      const firstSuccess = data.results.find((r) => r.status === "success") || data.results[0] || null;
      setActiveResult(firstSuccess);

      // Update queue statuses
      setQueue((prev) =>
        prev.map((item) => {
          const match = data.results.find((r) => r.filename === item.name);
          return {
            ...item,
            status: match?.status === "success" ? "completed" : "failed",
            result: match,
          };
        })
      );
    } catch (err: any) {
      const msg = err.message || "Failed to communicate with inference service.";
      setErrorMessage(
        `${msg}. Verify that the backend is healthy at ${apiUrl}.`
      );
      setQueue((prev) => prev.map((item) => ({ ...item, status: "failed" })));
    } finally {
      setIsRunning(false);
      setProgressText("");
    }
  };

  return (
    <div className="space-y-10">
      {/* Workspace Editorial Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-[#E8E4DD] pb-8">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#EDE7DE] text-charcoal-700 text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5 text-[#CC785C]" />
              <span>Interactive AI Workspace</span>
            </span>
            <span className="text-xs text-charcoal-400 font-mono">MobileNetV3-Small (PyTorch)</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-charcoal-900 tracking-tight leading-tight">
            Histopathology Stain-Shift Inference
          </h1>
          <p className="text-sm sm:text-base text-charcoal-600 max-w-2xl leading-relaxed">
            Upload colorectal adenocarcinoma patches, apply physics-informed Beer-Lambert stain variations,
            and inspect real model predictions with full 9-class softmax distributions.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <BackendStatusIndicator
            apiUrl={apiUrl}
            onApiUrlChange={setApiUrl}
            onHealthUpdate={setBackendHealth}
          />
        </div>
      </div>

      {/* Main Two-Column Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Control Panel (5 Cols) */}
        <div className="lg:col-span-5 space-y-6 bg-white p-6 rounded-2xl border border-[#E8E4DD] shadow-sm">
          {/* 1. Model Selector */}
          <ModelSelector
            selectedModel={selectedModel}
            onSelectModel={setSelectedModel}
          />

          {/* 2. Stain Shift Controls */}
          <StainControls
            selectedCondition={selectedCondition}
            onSelectCondition={setSelectedCondition}
            intensity={intensity}
            onIntensityChange={setIntensity}
          />

          {/* 3. Image Uploader */}
          <ImageUploader
            queue={queue}
            onAddFiles={handleAddFiles}
            onRemoveFile={handleRemoveFile}
            onClearQueue={handleClearQueue}
            disabled={isRunning}
          />

          {/* Error Notice */}
          {errorMessage && (
            <div className="p-3.5 bg-[#FBEFEF] border border-[#F2D6D6] rounded-xl text-xs text-[#9B2A2A] space-y-1">
              <p className="font-semibold">Inference Request Failed</p>
              <p className="text-[11px] leading-relaxed font-mono">{errorMessage}</p>
            </div>
          )}

          {/* Run Prediction Button */}
          <div className="space-y-2 pt-2">
            <button
              type="button"
              onClick={handleRunPrediction}
              disabled={isRunning || queue.length === 0}
              className={`w-full py-3.5 px-4 rounded-xl font-medium text-sm text-white shadow-sm transition flex items-center justify-center gap-2 ${
                isRunning || queue.length === 0
                  ? "bg-[#DDD8CF] text-charcoal-400 cursor-not-allowed shadow-none"
                  : "bg-charcoal-900 hover:bg-charcoal-800 active:scale-[0.99]"
              }`}
            >
              {isRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-white" />
                  <span>{progressText || "Computing Predictions..."}</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white text-white" />
                  <span>
                    Run Prediction {queue.length > 0 ? `(${queue.length} file${queue.length !== 1 ? "s" : ""})` : ""}
                  </span>
                </>
              )}
            </button>

            <p className="text-[10px] text-charcoal-400 text-center">
              Direct PyTorch forward pass on active device. Zero synthetic logits or browser simulations.
            </p>
          </div>
        </div>

        {/* Right Preview & Prediction Panel (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          <PredictionResultView
            result={activeResult}
            activeModelId={selectedModel}
          />
        </div>
      </div>

      {/* Bottom Batch Results Table & CSV Export */}
      {results.length > 0 && (
        <BatchResultsTable
          results={results}
          summary={summary}
          selectedFilename={activeResult?.filename || null}
          onSelectResult={(res) => setActiveResult(res)}
          onClearResults={handleClearResults}
        />
      )}

      {/* Secondary Navigation & Research Resources */}
      <div className="border-t border-[#E8E4DD] pt-10 mt-16 space-y-6">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-charcoal-500">
            Empirical Benchmark & Exploration
          </span>
          <span className="text-xs text-charcoal-400 font-mono">CRC-VAL-HE-7K Single-Cohort Study</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            href="/dashboard/"
            className="p-6 rounded-2xl bg-white border border-[#E8E4DD] hover:border-[#CC785C] hover:shadow-warm transition group flex flex-col justify-between"
          >
            <div>
              <div className="w-9 h-9 rounded-full bg-[#FAF4ED] text-[#CC785C] flex items-center justify-center mb-3 group-hover:bg-[#CC785C] group-hover:text-white transition">
                <BarChart2 className="w-4 h-4" />
              </div>
              <h3 className="font-serif text-lg font-medium text-charcoal-900">
                Results Dashboard
              </h3>
              <p className="text-xs text-charcoal-500 mt-1 leading-relaxed">
                Full 1,077-patch held-out evaluation across all 8 stain conditions.
                Inspect accuracy recovery from 33.89% to 97.68% and hardware execution benchmarks.
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#CC785C] mt-4">
              <span>View benchmark charts</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition" />
            </span>
          </Link>

          <Link
            href="/demo/"
            className="p-6 rounded-2xl bg-white border border-[#E8E4DD] hover:border-[#CC785C] hover:shadow-warm transition group flex flex-col justify-between"
          >
            <div>
              <div className="w-9 h-9 rounded-full bg-[#FAF4ED] text-[#CC785C] flex items-center justify-center mb-3 group-hover:bg-[#CC785C] group-hover:text-white transition">
                <Eye className="w-4 h-4" />
              </div>
              <h3 className="font-serif text-lg font-medium text-charcoal-900">
                Verified Precomputed Demo
              </h3>
              <p className="text-xs text-charcoal-500 mt-1 leading-relaxed">
                Deterministic 72-patch explorer with verified predictions generated directly from Stage A weights.
                Requires zero active backend connection.
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#CC785C] mt-4">
              <span>Explore sample patches</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition" />
            </span>
          </Link>
        </div>
      </div>
    </div>
  );
}
