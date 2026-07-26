'use client';

/**
 * Documents Page Client Component
 */

import { useDocuments, useDeleteDocument } from '@/features/documents/hooks/use-documents';
import { StatusBadge } from '@/features/upload/components/status-badge';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function DocumentsPageClient() {
  const { data, isLoading, error, refetch } = useDocuments();
  const deleteMutation = useDeleteDocument();

  const documents = data?.documents ?? [];

  return (
    <div style={{ minHeight: "calc(100vh - 48px)", backgroundColor: "#0B0E11" }}>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Document Library</h1>
            <p className="text-white/50 mt-1 text-sm">
              {data?.pagination.total ?? 0} documents in your knowledge base
            </p>
          </div>
          <a
            href="/documents/upload"
            id="nav-upload-btn"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
          >
            + Upload Document
          </a>
        </div>

        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-white/5 animate-pulse" />
            ))}
          </div>
        )}

        {error && (
          <div className="p-5 rounded-xl border border-red-500/30 bg-red-500/10 text-center">
            <p className="text-red-400 text-sm">Failed to load documents</p>
            <button onClick={() => refetch()} className="text-sm text-white/50 underline mt-2">Retry</button>
          </div>
        )}

        {!isLoading && !error && documents.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="text-5xl mb-4">📂</div>
            <h2 className="text-xl font-semibold text-white">No documents yet</h2>
            <p className="text-white/40 mt-2 text-sm">
              Upload your first industrial document to start building your knowledge base.
            </p>
            <a
              href="/documents/upload"
              className="mt-6 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
            >
              Upload Document
            </a>
          </div>
        )}

        {documents.length > 0 && (
          <div className="rounded-2xl border border-white/10 bg-slate-900/50 overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[1fr_80px_100px_140px_40px] gap-4 px-4 py-3 border-b border-white/10 text-xs text-white/40 uppercase tracking-wide font-medium">
              <span>Document</span>
              <span>Type</span>
              <span>Size</span>
              <span>Uploaded</span>
              <span></span>
            </div>

            {/* Rows */}
            <div className="divide-y divide-white/5">
              {documents.map((doc) => (
                <div
                  id={`doc-row-${doc.id}`}
                  key={doc.id}
                  className="grid grid-cols-[1fr_80px_100px_140px_40px] gap-4 items-center px-4 py-4 hover:bg-white/5 transition-colors group"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{doc.filename}</p>
                    <StatusBadge status={doc.status} className="mt-1" />
                  </div>
                  <span className="text-xs font-semibold text-white/50 uppercase">{doc.file_type}</span>
                  <span className="text-xs text-white/50">{formatBytes(doc.file_size)}</span>
                  <span className="text-xs text-white/40">{formatDate(doc.upload_time)}</span>
                  <button
                    id={`delete-doc-${doc.id}`}
                    onClick={() => {
                      if (confirm('Delete this document?')) deleteMutation.mutate(doc.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 w-7 h-7 flex items-center justify-center rounded hover:bg-red-500/20 text-white/20 hover:text-red-400 transition-all"
                    title={`Delete ${doc.filename}`}
                  >
                    🗑
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
