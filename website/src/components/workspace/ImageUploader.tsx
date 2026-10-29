"use client";

import React, { useRef, useState } from "react";
import { UploadCloud, FileImage, Archive, Trash2, AlertCircle, CheckCircle } from "lucide-react";
import { QueueFileItem } from "@/lib/types";

interface Props {
  queue: QueueFileItem[];
  onAddFiles: (newFiles: File[]) => void;
  onRemoveFile: (id: string) => void;
  onClearQueue: () => void;
  disabled?: boolean;
}

const SUPPORTED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".zip"];

export function ImageUploader({
  queue,
  onAddFiles,
  onRemoveFile,
  onClearQueue,
  disabled = false,
}: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onAddFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onAddFiles(Array.from(e.target.files));
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
          3. Upload Pathology Images
        </label>
        {queue.length > 0 && (
          <button
            type="button"
            onClick={onClearQueue}
            disabled={disabled}
            className="text-[11px] text-red-600 hover:text-red-800 font-medium disabled:opacity-50"
          >
            Clear Queue
          </button>
        )}
      </div>

      {/* Drag & Drop Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
          isDragging
            ? "border-brand-500 bg-brand-50/50"
            : "border-slate-300 hover:border-brand-400 bg-slate-50/60"
        } ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".png,.jpg,.jpeg,.tif,.tiff,.zip"
          onChange={handleFileChange}
          disabled={disabled}
          className="hidden"
          aria-label="Upload pathology images or ZIP file"
        />

        <div className="flex flex-col items-center gap-2">
          <div className="w-10 h-10 rounded-full bg-brand-50 flex items-center justify-center text-brand-600">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-800">
              Drop images or ZIP archive here
            </span>
            <span className="text-xs text-slate-500"> or browse files</span>
          </div>
          <p className="text-[11px] text-slate-400">
            Supports single image, batch files, or dataset ZIP (PNG, JPG, TIFF)
          </p>
        </div>
      </div>

      {/* Queue Preview List */}
      {queue.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>{queue.length} file{queue.length !== 1 ? "s" : ""} in queue</span>
            <span>
              {queue.filter((f) => f.status === "completed").length} completed
            </span>
          </div>

          <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1 divide-y divide-slate-100">
            {queue.map((item) => {
              const isZip = item.name.toLowerCase().endsWith(".zip");
              return (
                <div
                  key={item.id}
                  className="flex items-center justify-between pt-1.5 text-xs bg-white p-2 rounded-lg border border-slate-200/80 shadow-xs"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {/* Thumbnail preview */}
                    {item.previewUrl ? (
                      <img
                        src={item.previewUrl}
                        alt={item.name}
                        className="w-8 h-8 rounded object-cover border border-slate-200 flex-shrink-0"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-400 flex-shrink-0">
                        {isZip ? <Archive className="w-4 h-4 text-brand-600" /> : <FileImage className="w-4 h-4" />}
                      </div>
                    )}

                    <div className="min-w-0">
                      <p className="font-medium text-slate-900 truncate max-w-[160px] sm:max-w-[200px]">
                        {item.name}
                      </p>
                      <p className="text-[10px] text-slate-400">
                        {(item.size / 1024).toFixed(1)} KB {isZip ? "• ZIP Archive" : ""}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {item.status === "completed" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                        Done
                      </span>
                    )}
                    {item.status === "processing" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-50 text-brand-700 font-semibold animate-pulse">
                        Predicting...
                      </span>
                    )}
                    {item.status === "failed" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-700 font-semibold">
                        Error
                      </span>
                    )}

                    {!disabled && (
                      <button
                        type="button"
                        onClick={() => onRemoveFile(item.id)}
                        className="p-1 text-slate-400 hover:text-red-600 rounded transition"
                        title="Remove file"
                        aria-label={`Remove ${item.name}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
