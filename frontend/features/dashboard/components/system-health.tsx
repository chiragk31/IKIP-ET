"use client";

/**
 * SystemHealth — System Health Widget
 *
 * Dense status board: one row per service.
 * Dot + service name + latency (monospace).
 * NOT individual large cards — systems status board convention.
 */

import { useDashboardSystem } from "../hooks/use-dashboard";
import { WidgetSkeleton } from "./widget-skeleton";
import { WidgetError } from "./widget-error";
import type { ServiceHealth } from "../types";

const SERVICE_LABELS: Record<string, string> = {
  api:      "API Gateway",
  supabase: "Supabase DB",
  neo4j:    "Neo4j Graph",
  pinecone: "Pinecone Vectors",
  gemini:   "Gemini AI",
};

function statusColor(status: string): string {
  if (status === "up" || status === "healthy") return "#4ADE80";
  if (status === "degraded") return "#F5A623";
  return "#E5484D";
}

function statusLabel(status: string): string {
  if (status === "up" || status === "healthy") return "UP";
  if (status === "degraded") return "DEGRADED";
  return "DOWN";
}

interface ServiceRowProps {
  serviceKey: string;
  health: ServiceHealth;
}

function ServiceRow({ serviceKey, health }: ServiceRowProps) {
  const color = statusColor(health.status);
  const label = statusLabel(health.status);
  const displayName = SERVICE_LABELS[serviceKey] ?? serviceKey.toUpperCase();

  return (
    <div
      className="hover-elevate"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "8px 14px",
        borderBottom: "1px solid #2A333B",
      }}
    >
      {/* Status dot */}
      <span
        style={{
          width: "7px",
          height: "7px",
          borderRadius: "50%",
          backgroundColor: color,
          boxShadow: health.status === "up" || health.status === "healthy"
            ? `0 0 4px ${color}`
            : "none",
          flexShrink: 0,
        }}
        aria-label={`${displayName} status: ${label}`}
      />

      {/* Service name */}
      <span
        style={{
          flex: 1,
          fontSize: "12px",
          fontWeight: 500,
          color: "#E8ECEF",
          fontFamily: "'IBM Plex Sans', sans-serif",
        }}
      >
        {displayName}
      </span>

      {/* Status text */}
      <span
        className="font-mono"
        style={{
          fontSize: "10px",
          fontWeight: 600,
          letterSpacing: "0.06em",
          color,
        }}
      >
        {label}
      </span>

      {/* Latency */}
      <span
        className="font-mono"
        style={{
          fontSize: "10px",
          color: "#5A6472",
          minWidth: "50px",
          textAlign: "right" as const,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {health.latency_ms > 0
          ? `${health.latency_ms.toFixed(0)}ms`
          : "—"}
      </span>
    </div>
  );
}

export function SystemHealth() {
  const { data, isLoading, isError, refetch } = useDashboardSystem();

  const services = data?.services ?? {};
  const overallColor = statusColor(data?.overall ?? "down");

  return (
    <div className="widget widget-reveal" style={{ height: "100%" }}>
      <div className="widget-header">
        <span className="widget-title">System Health</span>
        {data && (
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: overallColor,
                boxShadow: data.overall === "healthy" ? `0 0 4px ${overallColor}` : "none",
              }}
              aria-hidden="true"
            />
            <span
              className="font-mono"
              style={{
                fontSize: "10px",
                fontWeight: 600,
                color: overallColor,
                letterSpacing: "0.06em",
              }}
            >
              {data.overall.toUpperCase()}
            </span>
          </div>
        )}
      </div>

      {isLoading && <WidgetSkeleton rows={5} height={28} />}

      {isError && (
        <WidgetError
          title="Health check unavailable"
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && (
        <>
          {Object.entries(services).map(([key, health]) => (
            <ServiceRow key={key} serviceKey={key} health={health} />
          ))}

          {data && (
            <div
              style={{
                padding: "6px 14px",
                fontSize: "10px",
                color: "#5A6472",
                fontFamily: "'IBM Plex Mono', monospace",
                borderTop: "1px solid #2A333B",
              }}
            >
              Checked {data.checked_at ? new Date(data.checked_at).toLocaleTimeString() : "—"} · {data.duration_ms}ms
            </div>
          )}
        </>
      )}
    </div>
  );
}
