/**
 * StatusBadge Component
 *
 * Displays a document processing status as a colored pill badge.
 */

'use client';

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  queued: {
    label: 'Queued',
    className: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
  },
  uploading: {
    label: 'Uploading',
    className: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  },
  uploaded: {
    label: 'Uploaded',
    className: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  },
  processing: {
    label: 'Processing',
    className: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  },
  parsing: {
    label: 'Parsing',
    className: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  },
  ocr_running: {
    label: 'OCR',
    className: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  },
  extracting: {
    label: 'Extracting',
    className: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  },
  building_graph: {
    label: 'Building Graph',
    className: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  },
  generating_embeddings: {
    label: 'Embedding',
    className: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  },
  summarizing: {
    label: 'Summarizing',
    className: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  },
  compliance_check: {
    label: 'Compliance',
    className: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  },
  completed: {
    label: 'Ready',
    className: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-500/20 text-red-300 border-red-500/30',
  },
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    className: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
  };

  const isActive = ['processing', 'parsing', 'ocr_running', 'extracting',
    'building_graph', 'generating_embeddings', 'summarizing', 'compliance_check', 'uploading'].includes(status);

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-xs font-medium
        ${config.className} ${className}
      `}
    >
      {isActive && (
        <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      )}
      {config.label}
    </span>
  );
}
