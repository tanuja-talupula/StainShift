"use client";

import React, { useState } from "react";
import { Download, CheckCircle2, AlertCircle, Clock, Trash2 } from "lucide-react";
import { BatchSummary, ImageInferenceResult } from "@/lib/types";

interface Props {
  results: ImageInferenceResult[];
  summary: BatchSummary | null;
  selectedFilename: string | null;
  onSelectResult: (res: ImageInferenceResult) => void;
  onClearResults: () => void;
}

export function BatchResultsTable({
  results,
  summary,
  selectedFilename,
  onSelectResult,
  onClearResults,
}: Props) {
  const [filterText, setFilterText] = useState("");

  if (results.length === 0) return null;

  const filteredResults = results.filter((r) =>
    r.filename.toLowerCase().includes(filterText.toLowerCase())
  );

  const handleDownloadCsv = () => {
    // Generate valid RFC-4180 CSV
    const headers = [
      "filename",
      "file_size_bytes",
      "model_id",
      "condition_applied",
      "intensity_applied",
      "predicted_class",
      "confidence",
      "probabilities_json",
      "inference_time_ms",
      "status",
      "error_message",
    ];

    const escapeCsv = (val: any) => {
      if (val === null || val === undefined) return '""';
      const str = String(val).replace(/"/g, '""');
      return `"${str}"`;
    };

    const rows = results.map((r) => {
      const primaryPred =
        r.predictions.robust_stain_aug ||
        r.predictions.baseline ||
        Object.values(r.predictions)[0];
      return [
        escapeCsv(r.filename),
        escapeCsv(r.file_size_bytes),
        escapeCsv(primaryPred?.model_id || "unknown"),
        escapeCsv(r.condition_applied),
        escapeCsv(r.intensity_applied),
        escapeCsv(primaryPred?.predicted_class || "N/A"),
        escapeCsv(primaryPred?.confidence ? (primaryPred.confidence * 100).toFixed(2) + "%" : "N/A"),
        escapeCsv(JSON.stringify(primaryPred?.probabilities || {})),
        escapeCsv(primaryPred?.inference_time_ms?.toFixed(2) || "N/A"),
        escapeCsv(r.status),
        escapeCsv(r.error_message || ""),
      ].join(",");
    });

    const csvContent = [headers.join(","), ...rows].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `stainshift_batch_inference_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] shadow-sm p-6 space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E8E4DD] pb-4">
        <div>
          <h3 className="font-serif text-xl font-medium text-charcoal-900">
            Batch Inference Results
          </h3>
          <p className="text-xs text-charcoal-500 mt-0.5">
            {results.length} image{results.length !== 1 ? "s" : ""} evaluated with actual trained weights.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDownloadCsv}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-charcoal-900 hover:bg-charcoal-800 text-white text-xs font-medium shadow-sm transition"
          >
            <Download className="w-3.5 h-3.5 text-white" />
            <span>Download CSV</span>
          </button>
          <button
            type="button"
            onClick={onClearResults}
            className="p-1.5 rounded-full text-charcoal-400 hover:text-charcoal-700 hover:bg-[#F3EFEA] transition"
            title="Clear all results"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E8E4DD] space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-charcoal-400">Total Files</span>
            <div className="text-xl font-serif font-bold text-charcoal-900">{summary.total_files}</div>
          </div>
          <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E8E4DD] space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#2D5A46]">Successful</span>
            <div className="text-xl font-serif font-bold text-[#2D5A46]">{summary.successful_files}</div>
          </div>
          <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E8E4DD] space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-charcoal-400">Avg Forward Latency</span>
            <div className="text-xl font-serif font-bold font-mono text-charcoal-900">
              {summary.average_inference_time_ms ? `${summary.average_inference_time_ms.toFixed(1)} ms` : "N/A"}
            </div>
          </div>
          <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E8E4DD] space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-charcoal-400">Class Distribution</span>
            <div className="text-xs font-mono text-charcoal-700 truncate">
              {Object.entries(summary.class_distribution || {})
                .map(([cls, cnt]) => `${cls}:${cnt}`)
                .join(" ") || "None"}
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex items-center justify-between gap-4">
        <input
          type="text"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder="Search filename..."
          className="w-full max-w-xs px-3.5 py-1.5 rounded-xl border border-[#E8E4DD] bg-white text-xs text-charcoal-800 placeholder-charcoal-400 focus:outline-none focus:ring-1 focus:ring-[#CC785C]"
        />
        <span className="text-xs text-charcoal-400 font-mono">
          Showing {filteredResults.length} of {results.length}
        </span>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto border border-[#E8E4DD] rounded-xl">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#FAF8F5] border-b border-[#E8E4DD] text-charcoal-500 font-medium">
            <tr>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Filename</th>
              <th className="py-2.5 px-3">Condition</th>
              <th className="py-2.5 px-3">Predicted Class</th>
              <th className="py-2.5 px-3">Confidence</th>
              <th className="py-2.5 px-3">Latency</th>
              <th className="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E8E4DD] font-mono text-[11px]">
            {filteredResults.map((row) => {
              const primaryPred =
                row.predictions.robust_stain_aug ||
                row.predictions.baseline ||
                Object.values(row.predictions)[0];
              const isSelected = row.filename === selectedFilename;

              return (
                <tr
                  key={row.filename}
                  className={`hover:bg-[#FAF8F5] cursor-pointer transition ${
                    isSelected ? "bg-[#F5F1EB] font-medium" : ""
                  }`}
                  onClick={() => onSelectResult(row)}
                >
                  <td className="py-2 px-3">
                    {row.status === "success" ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#2D5A46]" />
                    ) : (
                      <AlertCircle className="w-3.5 h-3.5 text-[#B83A3A]" />
                    )}
                  </td>
                  <td className="py-2 px-3 text-charcoal-900 font-sans font-medium truncate max-w-xs">
                    {row.filename}
                  </td>
                  <td className="py-2 px-3 text-charcoal-500 font-sans capitalize">
                    {row.condition_applied} ({row.intensity_applied.toFixed(1)}x)
                  </td>
                  <td className="py-2 px-3">
                    {primaryPred ? (
                      <span className="px-2 py-0.5 rounded-full bg-[#EDE7DE] text-charcoal-900 font-bold">
                        {primaryPred.predicted_class}
                      </span>
                    ) : (
                      <span className="text-charcoal-400">N/A</span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-charcoal-700">
                    {primaryPred ? `${(primaryPred.confidence * 100).toFixed(1)}%` : "N/A"}
                  </td>
                  <td className="py-2 px-3 text-charcoal-500">
                    {primaryPred?.inference_time_ms ? `${primaryPred.inference_time_ms.toFixed(1)} ms` : "N/A"}
                  </td>
                  <td className="py-2 px-3 text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectResult(row);
                      }}
                      className="px-2.5 py-1 rounded-full text-[10px] bg-white border border-[#E8E4DD] text-charcoal-700 hover:bg-[#F3EFEA] transition shadow-2xs font-sans"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
