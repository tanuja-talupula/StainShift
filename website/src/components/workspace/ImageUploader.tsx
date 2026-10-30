"use client";

import React, { useRef, useState } from "react";
import { UploadCloud, FileImage, Trash2, CheckCircle, AlertCircle } from "lucide-react";
import { QueueFileItem } from "@/lib/types";

interface Props {
  queue: QueueFileItem[];
  onAddFiles: (newFiles: File[]) => void;
  onRemoveFile: (id: string) => void;
  onClearQueue: () => void;
  disabled?: boolean;
}

const SUPPORTED_EXTENSIONS = [".png", ".jpg", ".jpeg"];

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
        <label className="text-xs font-semibold uppercase tracking-wider text-charcoal-700">
          3. Upload Histology Patches
        </label>
        {queue.length > 0 && (
          <button
            type="button"
            onClick={onClearQueue}
            disabled={disabled}
            className="text-[11px] text-charcoal-400 hover:text-charcoal-700 flex items-center gap-1 transition"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear</span>
          </button>
        )}
      </div>

      {/* Drag & Drop Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`relative border border-dashed rounded-2xl p-6 text-center cursor-pointer transition ${
          disabled
            ? "bg-[#F5F2EB] border-[#DDD7CC] opacity-60 cursor-not-allowed"
            : isDragging
            ? "border-charcoal-900 bg-[#F4EFEA]"
            : "border-[#DED8CE] bg-[#FAF8F5] hover:border-charcoal-400 hover:bg-[#F6F3ED]"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={SUPPORTED_EXTENSIONS.join(",")}
          onChange={handleFileChange}
          disabled={disabled}
          className="hidden"
          id="pathology-file-input"
        />

        <div className="flex flex-col items-center justify-center space-y-2">
          <div className="w-10 h-10 rounded-full bg-white border border-[#E8E4DD] flex items-center justify-center text-charcoal-600 shadow-sm">
            <UploadCloud className="w-5 h-5 text-charcoal-700" />
          </div>
          <div>
            <span className="text-xs font-medium text-charcoal-900">
              Drop histology patches here (PNG, JPG)
            </span>
            <span className="text-xs text-charcoal-500"> or </span>
            <span className="text-xs font-semibold text-[#CC785C] underline underline-offset-2">
              browse files
            </span>
          </div>
          <p className="text-[11px] text-charcoal-400">
            Select one or multiple patches for immediate inference
          </p>
        </div>
      </div>

      {/* Uploaded Queue Items */}
      {queue.length > 0 && (
        <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          <div className="flex items-center justify-between text-[11px] text-charcoal-400 px-1">
            <span>{queue.length} file{queue.length !== 1 ? "s" : ""} selected</span>
            <span>{queue.filter((q) => q.status === "completed").length} evaluated</span>
          </div>

          {queue.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between p-2 rounded-xl bg-white border border-[#E8E4DD] text-xs shadow-xs"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                {item.previewUrl ? (
                  <img
                    src={item.previewUrl}
                    alt={item.name}
                    className="w-8 h-8 rounded-lg object-cover border border-[#E8E4DD] flex-shrink-0"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-lg bg-[#FAF8F5] border border-[#E8E4DD] flex items-center justify-center flex-shrink-0">
                    <FileImage className="w-4 h-4 text-charcoal-400" />
                  </div>
                )}
                <div className="min-w-0">
                  <p className="font-mono text-xs text-charcoal-900 truncate">{item.name}</p>
                  <p className="text-[10px] text-charcoal-400">
                    {(item.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {item.status === "completed" && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-[#2D5A46] bg-[#EDF4EF] px-2 py-0.5 rounded-full">
                    <CheckCircle className="w-3 h-3 text-[#2D5A46]" />
                    <span>Done</span>
                  </span>
                )}
                {item.status === "failed" && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-[#B83A3A] bg-[#FBEFEF] px-2 py-0.5 rounded-full">
                    <AlertCircle className="w-3 h-3 text-[#B83A3A]" />
                    <span>Failed</span>
                  </span>
                )}
                {item.status === "processing" && (
                  <span className="text-[10px] font-mono text-charcoal-500 animate-pulse">
                    Processing...
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => onRemoveFile(item.id)}
                  disabled={disabled}
                  className="text-charcoal-300 hover:text-charcoal-700 p-1 rounded-full hover:bg-[#F3EFEA] transition"
                  title="Remove file"
                  aria-label={`Remove ${item.name}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
