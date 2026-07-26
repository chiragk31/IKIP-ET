'use client';

/**
 * Upload Page Client Component
 *
 * All interactive upload logic is in this client component.
 * The server page.tsx keeps metadata.
 */

import { useCallback } from 'react';
import { useUpload } from '@/features/upload/hooks/use-upload';
import { UploadZone } from '@/features/upload/components/upload-zone';
import { UploadProgress } from '@/features/upload/components/upload-progress';
import { UploadHistory } from '@/features/upload/components/upload-history';

export function UploadPageClient() {
  const {
    files,
    addFiles,
    removeFile,
    uploadAll,
    retryFile,
    clearCompleted,
    isUploading,
  } = useUpload();

  const pendingCount = files.filter((f) => f.status === 'idle').length;
  const successCount = files.filter((f) => f.status === 'success').length;

  const handleFilesSelected = useCallback((newFiles: File[]) => {
    addFiles(newFiles);
  }, [addFiles]);

  return (
    <div style={{ minHeight: "calc(100vh - 48px)", backgroundColor: "#0B0E11" }}>

      <main className="max-w-4xl mx-auto px-6 py-10 space-y-10">
        {/* Page Title */}
        <div>
          <h1 className="text-3xl font-bold text-white">Upload Documents</h1>
          <p className="text-white/50 mt-2 text-sm">
            Upload industrial documents for AI-powered knowledge extraction, graph building, and semantic search.
          </p>
        </div>

        {/* Upload Zone */}
        <section aria-label="File upload area">
          <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-6 space-y-4">
            <UploadZone
              onFilesSelected={handleFilesSelected}
              disabled={isUploading}
            />

            {/* Queued files */}
            {files.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-white/50 uppercase tracking-wide">
                    Files ({files.length})
                  </p>
                  {successCount > 0 && (
                    <button
                      id="clear-completed-btn"
                      onClick={clearCompleted}
                      className="text-xs text-white/40 hover:text-white/70 transition-colors"
                    >
                      Clear completed
                    </button>
                  )}
                </div>

                <div className="space-y-2">
                  {files.map((f) => (
                    <UploadProgress
                      key={f.id}
                      fileEntry={f}
                      onRemove={removeFile}
                      onRetry={retryFile}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Upload button */}
            {pendingCount > 0 && (
              <button
                id="upload-submit-btn"
                onClick={uploadAll}
                disabled={isUploading}
                className={`
                  w-full py-3 rounded-xl font-semibold text-sm transition-all
                  ${isUploading
                    ? 'bg-indigo-600/50 cursor-not-allowed text-white/50'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20'}
                `}
              >
                {isUploading
                  ? 'Uploading...'
                  : `Upload ${pendingCount} file${pendingCount > 1 ? 's' : ''}`}
              </button>
            )}
          </div>
        </section>

        {/* Upload History */}
        <section aria-label="Document upload history">
          <div className="rounded-2xl border border-white/10 bg-slate-900/50 p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">Document Library</h2>
                <p className="text-xs text-white/40 mt-0.5">
                  All uploaded documents and their processing status
                </p>
              </div>
              <a
                href="/documents"
                className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                View all →
              </a>
            </div>
            <UploadHistory />
          </div>
        </section>

        {/* Info cards */}
        <section aria-label="Supported document information" className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              icon: '📄',
              title: 'Documents',
              desc: 'PDF, DOCX, PPTX, XLSX, TXT, CSV',
            },
            {
              icon: '🖼',
              title: 'Images',
              desc: 'PNG, JPG, JPEG, TIFF (OCR-processed)',
            },
            {
              icon: '⚡',
              title: 'Processing',
              desc: 'AI extraction starts automatically in the background',
            },
          ].map((card) => (
            <div
              key={card.title}
              className="p-4 rounded-xl border border-white/10 bg-white/5"
            >
              <div className="text-2xl mb-2">{card.icon}</div>
              <p className="text-sm font-medium text-white">{card.title}</p>
              <p className="text-xs text-white/40 mt-1">{card.desc}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
