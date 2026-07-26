"use client";

/**
 * RecentDocuments — Recent Documents Widget
 *
 * Dense table layout of recent uploads.
 * Status indicators as filled squares (not rounded pills).
 * Clicking a row navigates to document detail.
 */

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { useDashboardDocuments } from "../hooks/use-dashboard";
import { WidgetSkeleton } from "./widget-skeleton";
import { WidgetError } from "./widget-error";
import { WidgetEmpty } from "./widget-empty";
import type { DashboardDocument } from "../types";

// Fallback if date-fns not available
function timeAgo(isoStr: string): string {
  try {
    return formatDistanceToNow(new Date(isoStr), { addSuffix: true });
  } catch {
    return isoStr;
  }
}

const STATUS_CONFIG: Record<string, { color: string; label: string; cls: string }> = {
  completed:  { color: "#4ADE80", label: "Ready",      cls: "completed" },
  processing: { color: "#3DDBD9", label: "Processing", cls: "processing" },
  queued:     { color: "#8A96A3", label: "Queued",     cls: "queued" },
  failed:     { color: "#E5484D", label: "Failed",     cls: "failed" },
};

function getStatus(doc: DashboardDocument) {
  return STATUS_CONFIG[doc.status] ?? { color: "#8A96A3", label: doc.status, cls: "queued" };
}

function DocRow({ doc }: { doc: DashboardDocument }) {
  const s = getStatus(doc);

  return (
    <div
      className="hover-elevate"
      style={{
        display: "grid",
        gridTemplateColumns: "8px 1fr 60px 80px 100px",
        alignItems: "center",
        gap: "10px",
        padding: "7px 14px",
        borderBottom: "1px solid #2A333B",
        cursor: "default",
      }}
    >
      {/* Status square */}
      <span
        className={`status-sq ${s.cls}`}
        title={s.label}
        aria-label={`Status: ${s.label}`}
      />

      {/* Filename */}
      <span
        style={{
          fontSize: "12px",
          fontWeight: 500,
          color: "#E8ECEF",
          fontFamily: "'IBM Plex Sans', sans-serif",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
        title={doc.filename}
      >
        {doc.filename}
      </span>

      {/* File type */}
      <span
        className="font-mono"
        style={{
          fontSize: "10px",
          color: "#8A96A3",
          textTransform: "uppercase",
        }}
      >
        {doc.file_type}
      </span>

      {/* Status text */}
      <span
        style={{
          fontSize: "10px",
          fontWeight: 500,
          color: s.color,
          fontFamily: "'IBM Plex Sans', sans-serif",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        {s.label}
      </span>

      {/* Time */}
      <span
        className="font-mono"
        style={{
          fontSize: "10px",
          color: "#5A6472",
          textAlign: "right" as const,
        }}
      >
        {timeAgo(doc.upload_time)}
      </span>
    </div>
  );
}

export function RecentDocuments() {
  const { data, isLoading, isError, refetch } = useDashboardDocuments();

  const headerStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "8px 1fr 60px 80px 100px",
    gap: "10px",
    padding: "6px 14px",
    borderBottom: "1px solid #2A333B",
    fontSize: "10px",
    fontWeight: 600,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: "#5A6472",
    fontFamily: "'IBM Plex Sans', sans-serif",
  };

  return (
    <div className="widget widget-reveal" style={{ height: "100%" }}>
      <div className="widget-header">
        <span className="widget-title">Recent Documents</span>
        {data && (
          <Link
            href="/documents/upload"
            style={{
              fontSize: "10px",
              color: "#3DDBD9",
              textDecoration: "none",
              fontFamily: "'IBM Plex Sans', sans-serif",
            }}
          >
            Upload →
          </Link>
        )}
      </div>

      {/* Column headers */}
      <div style={headerStyle}>
        <span />
        <span>Document</span>
        <span>Type</span>
        <span>Status</span>
        <span style={{ textAlign: "right" as const }}>Uploaded</span>
      </div>

      {isLoading && <WidgetSkeleton rows={6} height={30} />}

      {isError && (
        <WidgetError
          title="Documents unavailable"
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && (!data?.documents || data.documents.length === 0) && (
        <WidgetEmpty
          message="No documents uploaded yet."
          action="Upload Document"
          onAction={() => window.location.href = "/documents/upload"}
        />
      )}

      {!isLoading && !isError && data?.documents && data.documents.length > 0 && (
        <div style={{ overflowY: "auto", maxHeight: "280px" }}>
          {data.documents.map((doc) => (
            <DocRow key={doc.id} doc={doc} />
          ))}
        </div>
      )}
    </div>
  );
}
