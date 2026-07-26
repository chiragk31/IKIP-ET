/**
 * useUpload Hook
 *
 * Manages multi-file upload state, validation, and API submission.
 *
 * Features:
 * - Client-side validation (size, type) before sending to backend
 * - Per-file progress tracking
 * - Success / error state per file
 * - Retry support
 */

'use client';

import { useState, useCallback } from 'react';
import { UploadService } from '../services/upload-service';
import { UploadedFile, UploadStatus, MAX_UPLOAD_SIZE_BYTES, UPLOAD_ACCEPTED_TYPES } from '../types';

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function validateFile(file: File): string | null {
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return `File is too large. Maximum size is 50 MB. (${(file.size / 1024 / 1024).toFixed(1)} MB)`;
  }

  const acceptedMimes = Object.keys(UPLOAD_ACCEPTED_TYPES);
  if (!acceptedMimes.includes(file.type)) {
    // Fallback: check extension
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const allExts = (Object.values(UPLOAD_ACCEPTED_TYPES) as unknown as string[][]).flat();
    if (!allExts.includes(ext)) {
      return `Unsupported file type: ${file.type || ext}. Upload PDF, DOCX, PPTX, XLSX, TXT, CSV, or images.`;
    }
  }

  return null;
}

export interface UseUploadReturn {
  files: (UploadedFile & { id: string })[];
  addFiles: (newFiles: File[]) => void;
  removeFile: (id: string) => void;
  uploadAll: () => Promise<void>;
  retryFile: (id: string) => Promise<void>;
  clearCompleted: () => void;
  isUploading: boolean;
}

export function useUpload(): UseUploadReturn {
  const [files, setFiles] = useState<(UploadedFile & { id: string })[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  /** Add files to the queue. Validates each file before adding. */
  const addFiles = useCallback((newFiles: File[]) => {
    const entries = newFiles.map((file) => {
      const error = validateFile(file);
      return {
        id: generateId(),
        file,
        status: (error ? 'error' : 'idle') as UploadStatus,
        progress: 0,
        error: error ?? undefined,
      };
    });
    setFiles((prev) => [...prev, ...entries]);
  }, []);

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setFiles((prev) => prev.filter((f) => f.status !== 'success'));
  }, []);

  /** Upload a single file entry by its list ID. */
  const uploadSingle = useCallback(async (id: string) => {
    const entry = files.find((f) => f.id === id);
    if (!entry || entry.status === 'success') return;

    // Set to uploading
    setFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, status: 'uploading', progress: 0, error: undefined } : f))
    );

    try {
      const result = await UploadService.uploadFile(entry.file, (percent) => {
        setFiles((prev) =>
          prev.map((f) => (f.id === id ? { ...f, progress: percent } : f))
        );
      });

      setFiles((prev) =>
        prev.map((f) =>
          f.id === id
            ? { ...f, status: 'success', progress: 100, documentId: result.document_id }
            : f
        )
      );
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setFiles((prev) =>
        prev.map((f) => (f.id === id ? { ...f, status: 'error', error: message } : f))
      );
    }
  }, [files]);

  /** Upload all idle files in the queue. */
  const uploadAll = useCallback(async () => {
    setIsUploading(true);
    const idleFiles = files.filter((f) => f.status === 'idle');
    await Promise.allSettled(idleFiles.map((f) => uploadSingle(f.id)));
    setIsUploading(false);
  }, [files, uploadSingle]);

  /** Retry a failed upload. */
  const retryFile = useCallback(async (id: string) => {
    setFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, status: 'idle', error: undefined, progress: 0 } : f))
    );
    // Small delay to allow state update
    await new Promise((r) => setTimeout(r, 50));
    await uploadSingle(id);
  }, [uploadSingle]);

  return { files, addFiles, removeFile, uploadAll, retryFile, clearCompleted, isUploading };
}
