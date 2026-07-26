/**
 * UploadHistory Component
 *
 * Displays the list of all uploaded documents from the backend API.
 * Uses TanStack Query with auto-polling every 10s.
 */

'use client';

import { useDocuments, useDeleteDocument } from '@/features/documents/hooks/use-documents';
import { StatusBadge } from './status-badge';
import { DocumentListItem } from '@/features/documents/services/document-service';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function FileTypePill({ type }: { type: string }) {
  const colors: Record<string, string> = {
    pdf: 'text-red-400 bg-red-400/10',
    docx: 'text-indigo-400 bg-indigo-400/10',
    pptx: 'text-orange-400 bg-orange-400/10',
    xlsx: 'text-emerald-400 bg-emerald-400/10',
    csv: 'text-emerald-400 bg-emerald-400/10',
    txt: 'text-slate-400 bg-slate-400/10',
    png: 'text-blue-400 bg-blue-400/10',
    jpg: 'text-blue-400 bg-blue-400/10',
    jpeg: 'text-blue-400 bg-blue-400/10',
    tiff: 'text-blue-400 bg-blue-400/10',
  };
  const cls = colors[type.toLowerCase()] ?? 'text-slate-400 bg-slate-400/10';
  return (
    <span className={`px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wide ${cls}`}>
      {type}
    </span>
  );
}

interface DocumentRowProps {
  doc: DocumentListItem;
  onDelete: (id: string) => void;
  isDeleting: boolean;
}

function DocumentRow({ doc, onDelete, isDeleting }: DocumentRowProps) {
  return (
    <div
      id={`document-row-${doc.id}`}
      className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/5 transition-colors group"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-sm font-medium text-white truncate max-w-[280px]">
            {doc.filename}
          </p>
          <FileTypePill type={doc.file_type} />
        </div>
        <div className="flex items-center gap-3 text-xs text-white/40">
          <span>{formatBytes(doc.file_size)}</span>
          <span>·</span>
          <span>{formatDate(doc.upload_time)}</span>
        </div>
      </div>

      <StatusBadge status={doc.status} />

      <button
        id={`delete-document-${doc.id}`}
        onClick={() => onDelete(doc.id)}
        disabled={isDeleting}
        className="opacity-0 group-hover:opacity-100 w-7 h-7 flex items-center justify-center rounded-lg hover:bg-red-500/20 text-white/30 hover:text-red-400 transition-all"
        title="Delete document"
        aria-label={`Delete ${doc.filename}`}
      >
        🗑
      </button>
    </div>
  );
}

export function UploadHistory() {
  const { data, isLoading, error, refetch } = useDocuments();
  const deleteMutation = useDeleteDocument();

  const handleDelete = (id: string) => {
    if (confirm('Delete this document? This cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 rounded-xl bg-white/5 animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 text-sm">
        Failed to load documents.{' '}
        <button onClick={() => refetch()} className="underline hover:no-underline">
          Retry
        </button>
      </div>
    );
  }

  const documents = data?.documents ?? [];

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-white/40">
        <div className="text-4xl mb-3">📄</div>
        <p className="text-sm font-medium">No documents yet</p>
        <p className="text-xs mt-1">Upload your first document above</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {documents.map((doc) => (
        <DocumentRow
          key={doc.id}
          doc={doc}
          onDelete={handleDelete}
          isDeleting={deleteMutation.isPending}
        />
      ))}

      {data?.pagination && data.pagination.total > data.pagination.limit && (
        <p className="text-xs text-center text-white/30 pt-2">
          Showing {documents.length} of {data.pagination.total} documents
        </p>
      )}
    </div>
  );
}
