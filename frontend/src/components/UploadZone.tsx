"use client";

import React, { useRef, useState } from 'react';
import { apiClient } from '@/lib/axios';

interface UploadZoneProps {
  onUploadSuccess: () => void;
  compact?: boolean;
}

export default function UploadZone({ onUploadSuccess, compact }: UploadZoneProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStats, setUploadStats] = useState<{ total: number; ignored: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const allFiles = Array.from(e.target.files);
    
    // Explicitly filter for PDF files only
    const pdfFiles = allFiles.filter(file => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'));
    const ignoredCount = allFiles.length - pdfFiles.length;

    if (pdfFiles.length === 0) {
      alert(`No PDF files found in the selection. Ignored ${ignoredCount} non-PDF file(s).`);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setUploadStats({ total: pdfFiles.length, ignored: ignoredCount });

    const formData = new FormData();
    pdfFiles.forEach((file) => {
      formData.append('files', file);
      // webkitRelativePath contains the actual folder structure (e.g., "ParentFolder/SubFolder/document.pdf")
      formData.append('paths', file.webkitRelativePath || file.name); 
    });

    try {
      setIsUploading(true);
      // Sending to a simplified global upload endpoint
      await apiClient.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      onUploadSuccess();
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Failed to upload folder structure.");
    } finally {
      setIsUploading(false);
    }
  };

    return (
    <div>
        <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
        multiple
        // @ts-ignore
        webkitdirectory="true"
        />

        {compact ? (
        <button
            onClick={() => {
            setUploadStats(null);
            fileInputRef.current?.click();
            }}
            disabled={isUploading}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50"
        >
            {isUploading ? "Uploading..." : "Upload"}
        </button>
        ) : (
        <div className="p-6 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 text-center">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
            Upload Folders
            </h3>

            <p className="text-sm text-gray-500 mb-4">
            Select a nested directory. Non-PDF files will be automatically ignored.
            </p>

            <div className="flex flex-col items-center gap-2">
            <button
                onClick={() => {
                setUploadStats(null);
                fileInputRef.current?.click();
                }}
                disabled={isUploading}
                className="px-5 py-2 bg-blue-600 text-white font-medium rounded shadow hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
                {isUploading ? "Processing & Uploading..." : "Choose Folder to Sync"}
            </button>

            {uploadStats && (
                <p className="text-xs text-gray-600 mt-2">
                Queueing{" "}
                <span className="font-semibold text-blue-600">
                    {uploadStats.total} PDFs
                </span>
                {uploadStats.ignored > 0 &&
                    ` (Ignored ${uploadStats.ignored} non-PDF files)`}
                </p>
            )}
            </div>
        </div>
        )}
    </div>
    );
}