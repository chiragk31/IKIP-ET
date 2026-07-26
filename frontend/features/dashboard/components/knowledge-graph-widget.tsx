"use client";

/**
 * KnowledgeGraphWidget — Interactive Graph Visualization
 *
 * ReactFlow v11 (reactflow package) graph visualization.
 * Canvas: --canvas (#0B0E11)
 * Nodes: 5-color subset from signal palette (by entity type)
 * Edges: --border-adjacent grey, --signal-cyan on hover/selection
 * Supports: zoom, pan, node selection. Read-only (no editing).
 */

import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";
import { useDashboardGraph } from "../hooks/use-dashboard";
import { WidgetSkeleton } from "./widget-skeleton";
import { WidgetError } from "./widget-error";
import { WidgetEmpty } from "./widget-empty";
import type { DashboardGraphNode } from "../types";

// Restrained 5-color palette by entity type
const ENTITY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  Asset:        { bg: "#1D2A32", border: "#F5A623", text: "#F5A623" },
  Failure:      { bg: "#2A1A1A", border: "#E5484D", text: "#E5484D" },
  Person:       { bg: "#1A2A24", border: "#4ADE80", text: "#4ADE80" },
  Location:     { bg: "#1A222A", border: "#3DDBD9", text: "#3DDBD9" },
  Document:     { bg: "#1D242B", border: "#8A96A3", text: "#8A96A3" },
  Procedure:    { bg: "#1D2A32", border: "#3DDBD9", text: "#3DDBD9" },
  Event:        { bg: "#251D2A", border: "#8A96A3", text: "#8A96A3" },
  Measurement:  { bg: "#1A2A24", border: "#4ADE80", text: "#4ADE80" },
  Risk:         { bg: "#2A1A1A", border: "#F5A623", text: "#F5A623" },
  Regulation:   { bg: "#1A222A", border: "#8A96A3", text: "#8A96A3" },
  Organization: { bg: "#1D242B", border: "#8A96A3", text: "#8A96A3" },
  Concept:      { bg: "#1D242B", border: "#5A6472", text: "#5A6472" },
};

const DEFAULT_COLOR = { bg: "#1D242B", border: "#3A4450", text: "#8A96A3" };

function buildFlowNodes(graphNodes: DashboardGraphNode[]): Node[] {
  const cols = Math.ceil(Math.sqrt(graphNodes.length));
  return graphNodes.slice(0, 50).map((node, i) => {
    const colors = ENTITY_COLORS[node.entity_type] ?? DEFAULT_COLOR;
    const col = i % cols;
    const row = Math.floor(i / cols);

    return {
      id: node.entity_id,
      position: {
        x: col * 180 + (row % 2 === 0 ? 0 : 90),
        y: row * 100,
      },
      data: {
        label: (
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontSize: "8px",
                fontWeight: 600,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: colors.text,
                marginBottom: "2px",
                fontFamily: "'IBM Plex Sans', sans-serif",
              }}
            >
              {node.entity_type}
            </div>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 500,
                color: "#E8ECEF",
                maxWidth: "130px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontFamily: "'IBM Plex Sans', sans-serif",
              }}
            >
              {node.label}
            </div>
          </div>
        ),
      },
      style: {
        backgroundColor: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: "2px",
        padding: "6px 10px",
        minWidth: "100px",
        fontSize: "11px",
        color: "#E8ECEF",
      },
    };
  });
}

export function KnowledgeGraphWidget() {
  const { data, isLoading, isError, refetch } = useDashboardGraph();
  const graphNodes = data?.nodes ?? [];

  const flowNodes = useMemo(() => buildFlowNodes(graphNodes), [graphNodes]);
  const flowEdges: Edge[] = [];

  const [nodes, , onNodesChange] = useNodesState(flowNodes);
  const [edges, , onEdgesChange] = useEdgesState(flowEdges);

  return (
    <div className="widget widget-reveal" style={{ height: "100%" }}>
      <div className="widget-header">
        <span className="widget-title">Knowledge Graph</span>
        {data && (
          <span className="font-mono" style={{ fontSize: "10px", color: "#5A6472" }}>
            {data.total_nodes} NODES
          </span>
        )}
      </div>

      <div style={{ height: "320px", position: "relative" }}>
        {isLoading && <WidgetSkeleton rows={8} height={14} />}

        {isError && (
          <WidgetError
            title="Graph unavailable"
            message="Knowledge graph data could not be loaded."
            onRetry={() => refetch()}
          />
        )}

        {!isLoading && !isError && graphNodes.length === 0 && (
          <WidgetEmpty message="No connected entities. Upload and process documents to build the knowledge graph." />
        )}

        {!isLoading && !isError && graphNodes.length > 0 && (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={true}
            zoomOnDoubleClick={true}
            style={{ backgroundColor: "#0B0E11" }}
            aria-label="Knowledge Graph visualization"
          >
            <Background
              variant={BackgroundVariant.Dots}
              color="#2A333B"
              size={1}
              gap={20}
            />
            <Controls />

            <MiniMap
              style={{
                backgroundColor: "#0B0E11",
                border: "1px solid #2A333B",
              }}
              nodeColor={(n) => {
                const typeKey = (n.data as { label: React.ReactNode; entityType?: string })?.entityType ?? "";
                return (ENTITY_COLORS[typeKey] ?? DEFAULT_COLOR).border;
              }}
              maskColor="rgba(11, 14, 17, 0.7)"
            />
          </ReactFlow>
        )}
      </div>

      {/* Entity type legend */}
      {!isLoading && !isError && graphNodes.length > 0 && (
        <div
          style={{
            padding: "8px 14px",
            borderTop: "1px solid #2A333B",
            display: "flex",
            flexWrap: "wrap",
            gap: "10px",
          }}
        >
          {Object.entries(ENTITY_COLORS).slice(0, 7).map(([type, colors]) => (
            <div
              key={type}
              style={{ display: "flex", alignItems: "center", gap: "4px" }}
            >
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "1px",
                  backgroundColor: colors.border,
                  flexShrink: 0,
                }}
                aria-hidden="true"
              />
              <span
                style={{
                  fontSize: "10px",
                  color: "#5A6472",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                }}
              >
                {type}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
