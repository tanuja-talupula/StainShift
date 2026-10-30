"use client";

import React, { useRef, useState } from "react";
import Link from "next/link";
import {
  Play,
  RefreshCw,
  ArrowLeft,
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
      const isImage = file.type.startsWith("image/") || /\.(png|jpe?g)$/i.test(file.name);
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
      setErrorMessage("Please select at least one histology patch to run prediction.");
      return;
    }

    setIsRunning(true);
    setErrorMessage(null);
    setProgressText(`Evaluating ${queue.length} patch${queue.length !== 1 ? "es" : ""}...`);

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
    <div className="space-y-12">
      {/* Page Header */}
      <section className="space-y-6 pt-2 pb-6 border-b border-[#E8E4DD]">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs text-charcoal-500 hover:text-charcoal-800 transition mb-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Overview
            </Link>
            <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-charcoal-900 tracking-tight leading-tight">
              AI Workspace
            </h1>
            <p className="text-sm sm:text-base text-charcoal-600 leading-relaxed">
              StainShift evaluates how synthetic histopathology stain variations affect CNN classification performance.
              Compare standard empirical training against physics-informed Beer-Lambert stain augmentation on colorectal tissue.
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
      </section>

      {/* Main Interactive AI Workspace */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#CC785C]" />
            <h2 className="font-serif text-xl font-medium text-charcoal-900">
              Interactive Inference
            </h2>
          </div>
          <span className="text-xs text-charcoal-400 font-mono">
            Workflow: Upload → Select Condition → Run Prediction
          </span>
        </div>

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
                    <span>{progressText || "Evaluating..."}</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white text-white" />
                    <span>
                      Run Prediction {queue.length > 0 ? `(${queue.length} patch${queue.length !== 1 ? "es" : ""})` : ""}
                    </span>
                  </>
                )}
              </button>

              <p className="text-[11px] text-charcoal-500 text-center">
                Live PyTorch inference using MobileNetV3-Small on CPU.
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
      </section>

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
    </div>
  );
}
