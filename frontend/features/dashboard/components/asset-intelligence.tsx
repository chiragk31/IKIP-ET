"use client";

/**
 * AssetIntelligence — Asset Intelligence Widget
 *
 * Dense table layout (not card grid per §Visual Design System).
 * Status indicators as small filled squares, not rounded pills.
 * Clicking an asset row navigates to Asset 360.
 */

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { useDashboardAssets } from "../hooks/use-dashboard";
import { WidgetSkeleton } from "./widget-skeleton";
import { WidgetError } from "./widget-error";
import { WidgetEmpty } from "./widget-empty";
import type { DashboardAsset } from "../types";

function AssetRow({ asset, index }: { asset: DashboardAsset; index: number }) {
  const entityId = asset.entity_id;

  return (
    <Link
      href={`/assets/${entityId}`}
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 120px 80px 80px 24px",
        alignItems: "center",
        gap: "10px",
        padding: "7px 14px",
        borderBottom: "1px solid #2A333B",
        textDecoration: "none",
        backgroundColor: "transparent",
        transition: "background-color 0.1s",
        cursor: "pointer",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = "#1D242B";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = "transparent";
      }}
      aria-label={`Asset: ${asset.name}`}
    >
      {/* Asset name */}
      <span
        style={{
          fontSize: "13px",
          fontWeight: 500,
          color: "#E8ECEF",
          fontFamily: "'IBM Plex Sans', sans-serif",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {asset.name}
      </span>

      {/* Type */}
      <span
        style={{
          fontSize: "11px",
          color: "#8A96A3",
          fontFamily: "'IBM Plex Sans', sans-serif",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {asset.entity_type ?? "—"}
      </span>

      {/* Location */}
      <span
        style={{
          fontSize: "11px",
          color: "#8A96A3",
          fontFamily: "'IBM Plex Sans', sans-serif",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {asset.location ?? "—"}
      </span>

      {/* Confidence */}
      <span
        className="font-mono"
        style={{
          fontSize: "11px",
          color: "#8A96A3",
          textAlign: "right" as const,
        }}
      >
        {asset.confidence != null
          ? `${(asset.confidence * 100).toFixed(0)}%`
          : "—"}
      </span>

      {/* External link icon */}
      <ExternalLink
        size={11}
        style={{ color: "#5A6472" }}
        aria-hidden="true"
      />
    </Link>
  );
}

export function AssetIntelligence() {
  const { data, isLoading, isError, refetch } = useDashboardAssets();

  const headerStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "1fr 120px 80px 80px 24px",
    gap: "10px",
    padding: "7px 14px",
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
        <span className="widget-title">Asset Intelligence</span>
        {data && (
          <span
            className="font-mono"
            style={{ fontSize: "10px", color: "#5A6472" }}
          >
            {data.total} ASSETS
          </span>
        )}
      </div>

      {/* Table header */}
      <div style={headerStyle}>
        <span>Asset</span>
        <span>Type</span>
        <span>Location</span>
        <span style={{ textAlign: "right" as const }}>Conf.</span>
        <span />
      </div>

      {/* Body */}
      {isLoading && <WidgetSkeleton rows={6} height={34} />}

      {isError && (
        <WidgetError
          title="Assets unavailable"
          message="Could not load asset data."
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && (!data?.assets || data.assets.length === 0) && (
        <WidgetEmpty message="No assets discovered yet. Upload documents to extract assets." />
      )}

      {!isLoading && !isError && data?.assets && data.assets.length > 0 && (
        <div style={{ overflowY: "auto", maxHeight: "320px" }}>
          {data.assets.map((asset, i) => (
            <AssetRow key={asset.entity_id ?? i} asset={asset} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
