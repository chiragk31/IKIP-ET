/**
 * UploadProgress Component
 *
 * Shows per-file upload progress with a progress bar, status, and actions.
 */

'use client';

import { UploadedFile } from '../types';

interface UploadProgressProps {
  fileEntry: UploadedFile & { id: string };
  onRemove: (id: string) => void;
  onRetry: (id: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function FileTypeIcon({ type }: { type: string }) {
  const ext = type.split('/').pop()?.toUpperCase() ?? 'FILE';
  const colors: Record<string, string> = {
    pdf: 'text-red-400',
    png: 'text-blue-400',
    jpeg: 'text-blue-400',
    jpg: 'text-blue-400',
    tiff: 'text-blue-400',
    docx: 'text-indigo-400',
    pptx: 'text-orange-400',
    xlsx: 'text-emerald-400',
    csv: 'text-emerald-400',
    plain: 'text-slate-400',
    default: 'text-slate-400',
  };
  const color = colors[ext.toLowerCase()] ?? colors.default;

  return (
    <div className={`w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[9px] font-bold ${color}`}>
      {ext.slice(0, 4)}
    </div>
  );
}

export function UploadProgress({ fileEntry, onRemove, onRetry }: UploadProgressProps) {
  const { id, file, status, progress, error } = fileEntry;

  const isProcessing = status === 'uploading' || status === 'validating';
  const isError = status === 'error';
  const isSuccess = status === 'success';

  return (
    <div className={`
      flex items-start gap-3 p-3 rounded-xl border transition-all
      ${isError ? 'border-red-500/30 bg-red-500/5' : ''}
      ${isSuccess ? 'border-emerald-500/30 bg-emerald-500/5' : ''}
      ${isProcessing ? 'border-indigo-500/30 bg-indigo-500/5' : ''}
      ${status === 'idle' ? 'border-white/10 bg-white/5' : ''}
    `}>
      <FileTypeIcon type={file.type} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <p className="text-sm font-medium text-white truncate max-w-[200px]">
            {file.name}
          </p>
          <span className="text-xs text-white/40 ml-2 shrink-0">
            {formatBytes(file.size)}
          </span>
        </div>

        {/* Progress Bar */}
        {isProcessing && (
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}

        {/* Status text */}
        {isProcessing && (
          <p className="text-xs text-white/50 mt-1">{progress}% uploaded</p>
        )}

        {isError && error && (
          <p className="text-xs text-red-400 mt-1 break-words">{error}</p>
        )}

        {isSuccess && (
          <p className="text-xs text-emerald-400 mt-1">✓ Queued for processing</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {isError && (
          <button
            id={`retry-upload-${id}`}
            onClick={() => onRetry(id)}
            className="px-2 py-1 text-xs rounded-lg bg-white/10 hover:bg-white/15 text-white/70 transition-colors"
            title="Retry upload"
          >
            Retry
          </button>
        )}
        {(status === 'idle' || isError || isSuccess) && (
          <button
            id={`remove-file-${id}`}
            onClick={() => onRemove(id)}
            className="w-6 h-6 flex items-center justify-center rounded-lg hover:bg-white/10 text-white/30 hover:text-white/70 transition-colors"
            title="Remove"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}
