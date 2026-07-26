"use client";

/**
 * OverviewCards — KPI Cards Widget
 *
 * 7 KPI cards displaying platform-wide metrics.
 * IBM Plex Mono required for all numeric values.
 * Recharts sparklines use --signal-cyan, no fill gradient.
 * Square indicators, not pills — instrument panel convention.
 */

import {
  FileText,
  Cpu,
  Share2,
  GitBranch,
  Layers,
  CheckSquare,
  XOctagon,
} from "lucide-react";
import { useDashboardOverview } from "../hooks/use-dashboard";
import { KpiSkeleton } from "./widget-skeleton";
import { WidgetError } from "./widget-error";
import type { DashboardOverview } from "../types";

interface KpiCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  accent?: string;
  subLabel?: string;
}

function KpiCard({ label, value, icon, accent = "#3DDBD9", subLabel }: KpiCardProps) {
  return (
    <div
      className="widget widget-reveal hover-elevate"
      style={{ cursor: "default" }}
    >
      <div style={{ padding: "14px 16px" }}>
        {/* Label row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "10px",
          }}
        >
          <span
            style={{
              fontSize: "10px",
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#8A96A3",
              fontFamily: "'IBM Plex Sans', sans-serif",
            }}
          >
            {label}
          </span>
          <span style={{ color: accent, opacity: 0.7 }}>{icon}</span>
        </div>

        {/* Primary value — IBM Plex Mono mandatory */}
        <div
          className="font-mono"
          style={{
            fontSize: "28px",
            fontWeight: 600,
            letterSpacing: "-0.02em",
            color: "#E8ECEF",
            lineHeight: 1,
            fontVariantNumeric: "tabular-nums",
          }}
          aria-label={`${label}: ${value}`}
        >
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>

        {subLabel && (
          <div
            style={{
              fontSize: "10px",
              color: "#5A6472",
              marginTop: "6px",
              fontFamily: "'IBM Plex Sans', sans-serif",
            }}
          >
            {subLabel}
          </div>
        )}

        {/* Accent line at bottom — visual anchor */}
        <div
          style={{
            marginTop: "12px",
            height: "1px",
            backgroundColor: accent,
            opacity: 0.2,
            width: "100%",
          }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}

interface OverviewCardsProps {
  data?: DashboardOverview;
}

function OverviewCardsContent({ data }: OverviewCardsProps) {
  const cards = [
    {
      label: "Total Documents",
      value: data?.documents.total ?? 0,
      icon: <FileText size={14} aria-hidden="true" />,
      accent: "#3DDBD9",
      subLabel: "All uploaded files",
    },
    {
      label: "Total Assets",
      value: data?.assets.total ?? 0,
      icon: <Cpu size={14} aria-hidden="true" />,
      accent: "#F5A623",
      subLabel: "In knowledge graph",
    },
    {
      label: "Graph Nodes",
      value: data?.graph.node_count ?? 0,
      icon: <Share2 size={14} aria-hidden="true" />,
      accent: "#3DDBD9",
      subLabel: "Entities extracted",
    },
    {
      label: "Relationships",
      value: data?.graph.relationship_count ?? 0,
      icon: <GitBranch size={14} aria-hidden="true" />,
      accent: "#3DDBD9",
      subLabel: "Graph edges",
    },
    {
      label: "Vectors",
      value: data?.embeddings.total_vectors ?? 0,
      icon: <Layers size={14} aria-hidden="true" />,
      accent: "#8A96A3",
      subLabel: "Pinecone embeddings",
    },
    {
      label: "Processed",
      value: data?.documents.completed ?? 0,
      icon: <CheckSquare size={14} aria-hidden="true" />,
      accent: "#4ADE80",
      subLabel: "Pipeline complete",
    },
    {
      label: "Failed",
      value: data?.documents.failed ?? 0,
      icon: <XOctagon size={14} aria-hidden="true" />,
      accent: data?.documents.failed ? "#E5484D" : "#8A96A3",
      subLabel: "Require attention",
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(7, 1fr)",
        gap: "1px",
        backgroundColor: "#2A333B",
      }}
      role="region"
      aria-label="Platform overview metrics"
    >
      {cards.map((card) => (
        <KpiCard key={card.label} {...card} />
      ))}
    </div>
  );
}

export function OverviewCards() {
  const { data, isLoading, isError, refetch } = useDashboardOverview();

  if (isLoading) {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: "1px",
          backgroundColor: "#2A333B",
        }}
      >
        {Array.from({ length: 7 }).map((_, i) => (
          <KpiSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="widget">
        <WidgetError
          title="Overview metrics unavailable"
          message="Failed to load KPI data."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return <OverviewCardsContent data={data} />;
}
