"use client";

import React, { useState } from "react";
import { Download, FileText, CheckCircle2, AlertCircle, Clock, Trash2, ArrowUpDown } from "lucide-react";
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
      "error_message"
    ];

    const escapeCsv = (val: any) => {
      if (val === null || val === undefined) return '""';
      const str = String(val).replace(/"/g, '""');
      return `"${str}"`;
    };

    const rows = results.map((r) => {
      // Pick the main prediction
      const primaryPred = r.predictions.robust_stain_aug || r.predictions.baseline || Object.values(r.predictions)[0];
      return [
        escapeCsv(r.filename),
        escapeCsv(r.file_size_bytes),
        escapeCsv(primaryPred?.model_id || "unknown"),
        escapeCsv(r.condition_applied),
        escapeCsv(r.intensity_applied),
        escapeCsv(primaryPred?.predicted_class || "N/A"),
        escapeCsv(primaryPred?.confidence !== undefined ? primaryPred.confidence.toFixed(4) : "N/A"),
        escapeCsv(primaryPred?.probabilities ? JSON.stringify(primaryPred.probabilities) : "{}"),
        escapeCsv(primaryPred?.inference_time_ms !== undefined ? primaryPred.inference_time_ms.toFixed(3) : "N/A"),
        escapeCsv(r.status),
        escapeCsv(r.error_message || "")
      ].join(",");
    });

    const csvContent = [headers.join(","), ...rows].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `stainshift_predictions_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
      {/* Batch Summary Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <h3 className="text-base font-bold text-slate-900">Batch Inference Results</h3>
          <p className="text-xs text-slate-500">
            {results.length} image{results.length !== 1 ? "s" : ""} evaluated with actual trained weights.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDownloadCsv}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download CSV</span>
          </button>
          <button
            type="button"
            onClick={onClearResults}
            className="p-1.5 rounded-lg border border-slate-200 text-slate-400 hover:text-red-600 transition"
            title="Clear Results"
            aria-label="Clear all results"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary KPIs */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">Total Files</span>
            <span className="text-lg font-extrabold font-mono text-slate-900">{summary.total_files}</span>
          </div>
          <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-200/80">
            <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-600 block">Successful</span>
            <span className="text-lg font-extrabold font-mono text-emerald-800">{summary.successful_files}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">Avg Forward Latency</span>
            <span className="text-lg font-extrabold font-mono text-slate-900">{summary.average_inference_time_ms} ms</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">Class Distribution</span>
            <span className="text-xs font-mono text-slate-700 block truncate">
              {Object.entries(summary.class_distribution).map(([c, n]) => `${c}:${n}`).join(", ") || "None"}
            </span>
          </div>
        </div>
      )}

      {/* Filter and Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <input
            type="text"
            placeholder="Search filename..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs w-full max-w-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <span className="text-xs text-slate-400">
            Showing {filteredResults.length} of {results.length}
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-xs text-left text-slate-700">
            <thead className="bg-slate-50 text-slate-900 font-semibold border-b border-slate-200">
              <tr>
                <th scope="col" className="py-2.5 px-3">Thumbnail</th>
                <th scope="col" className="py-2.5 px-3">Filename</th>
                <th scope="col" className="py-2.5 px-3">Condition</th>
                <th scope="col" className="py-2.5 px-3">Predicted Class</th>
                <th scope="col" className="py-2.5 px-3 text-right">Confidence</th>
                <th scope="col" className="py-2.5 px-3 text-right">Latency</th>
                <th scope="col" className="py-2.5 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredResults.map((item) => {
                const isSelected = selectedFilename === item.filename;
                const primaryPred = item.predictions.robust_stain_aug || item.predictions.baseline || Object.values(item.predictions)[0];
                return (
                  <tr
                    key={item.filename}
                    onClick={() => onSelectResult(item)}
                    className={`cursor-pointer transition hover:bg-slate-50 ${
                      isSelected ? "bg-brand-50/60 font-medium" : ""
                    }`}
                  >
                    <td className="py-2 px-3">
                      <div className="w-8 h-8 rounded bg-slate-100 overflow-hidden border border-slate-200">
                        {item.original_thumbnail_b64 ? (
                          <img
                            src={item.original_thumbnail_b64}
                            alt={item.filename}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <FileText className="w-4 h-4 text-slate-400 m-2" />
                        )}
                      </div>
                    </td>
                    <td className="py-2 px-3 font-mono font-medium text-slate-900 truncate max-w-[180px]">
                      {item.filename}
                    </td>
                    <td className="py-2 px-3 capitalize text-slate-600">
                      {item.condition_applied.replace(/_/g, " ")} ({item.intensity_applied.toFixed(2)}x)
                    </td>
                    <td className="py-2 px-3">
                      {primaryPred ? (
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-slate-900">{primaryPred.predicted_class}</span>
                          <span className="text-[11px] text-slate-500 truncate max-w-[120px]">
                            {primaryPred.predicted_class_description}
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-semibold text-brand-700">
                      {primaryPred ? `${(primaryPred.confidence * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-slate-500">
                      {primaryPred ? `${primaryPred.inference_time_ms.toFixed(1)} ms` : "—"}
                    </td>
                    <td className="py-2 px-3 text-center">
                      {item.status === "success" ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Success
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200" title={item.error_message || "Error"}>
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
