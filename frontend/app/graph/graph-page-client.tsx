"use client";

/**
 * GraphPageClient — Full-page Knowledge Graph Explorer
 *
 * Architecture:
 *   - Full-viewport ReactFlow canvas (left)
 *   - Slide-in detail panel (right) when a node is selected
 *   - Pagination controls to load more nodes
 *
 * Response shapes (verified against live API 2026-07-26):
 *
 *   GET /api/v1/graph/nodes
 *   data.items[]:   { entity_id, name, label, confidence, source_document, created_at }
 *   data.pagination: { page, limit, total }
 *
 *   GET /api/v1/graph/node/{entity_id}
 *   data.node.n:    { entity_id, name, entity_type, confidence, aliases, source_document,
 *                     properties, extraction_version, created_at }
 *   data.neighbors[]: { node_id, node_name, relationship, neighbor_id,
 *                       neighbor_name, neighbor_label }
 */

import { useCallback, useMemo, useState, useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { WidgetSkeleton } from "@/features/dashboard/components/widget-skeleton";
import { WidgetError } from "@/features/dashboard/components/widget-error";
import { WidgetEmpty } from "@/features/dashboard/components/widget-empty";

// ─── Types (matched exactly to live API responses) ───────────────────────────

interface GraphNodeItem {
  entity_id: string;
  name: string;
  label: string;       // "Asset", "Person", etc. — from LIST endpoint
  confidence: number | null;
  source_document: string | null;
  created_at: string | null;
}

interface GraphNodeDetail {
  entity_id: string;
  name: string;
  entity_type: string; // from NODE DETAIL endpoint (node.n shape)
  confidence: number | null;
  aliases: string[];
  source_document: string | null;
  properties: string | null;
  extraction_version: string | null;
  created_at: string | null;
}

interface NeighborItem {
  node_id: string;
  node_name: string;
  relationship: string;
  neighbor_id: string;
  neighbor_name: string;
  neighbor_label: string;
}

interface NodesResponse {
  items: GraphNodeItem[];
  pagination: { page: number; limit: number; total: number };
}

interface NodeDetailResponse {
  node: { n: GraphNodeDetail };
  neighbors: NeighborItem[];
}

// ─── Visual config ───────────────────────────────────────────────────────────

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

// ─── Node builder ─────────────────────────────────────────────────────────────

function buildFlowNodes(items: GraphNodeItem[]): Node[] {
  const cols = Math.max(1, Math.ceil(Math.sqrt(items.length)));
  return items.map((item, i) => {
    const colors = ENTITY_COLORS[item.label] ?? DEFAULT_COLOR;
    const col = i % cols;
    const row = Math.floor(i / cols);
    return {
      id: item.entity_id,
      position: {
        x: col * 200 + (row % 2 === 0 ? 0 : 100),
        y: row * 110,
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
              {item.label}
            </div>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 500,
                color: "#E8ECEF",
                maxWidth: "140px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontFamily: "'IBM Plex Sans', sans-serif",
              }}
            >
              {item.name}
            </div>
          </div>
        ),
        // store for minimap coloring
        entityLabel: item.label,
      },
      style: {
        backgroundColor: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: "2px",
        padding: "6px 10px",
        minWidth: "110px",
        cursor: "pointer",
      },
    };
  });
}

// ─── Node types — module-level constant to avoid ReactFlow warning ────────────

const NODE_TYPES = {} as const;
const EDGE_TYPES = {} as const;

// ─── Detail panel ─────────────────────────────────────────────────────────────

interface DetailPanelProps {
  entityId: string;
  data: NodeDetailResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  onClose: () => void;
}

function DetailPanel({ entityId, data, isLoading, isError, onClose }: DetailPanelProps) {
  const node = data?.node?.n;
  const neighbors = data?.neighbors ?? [];
  const colors = ENTITY_COLORS[node?.entity_type ?? ""] ?? DEFAULT_COLOR;

  return (
    <aside
      style={{
        width: "340px",
        flexShrink: 0,
        backgroundColor: "#151A1F",
        borderLeft: "1px solid #2A333B",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
      aria-label="Node details"
    >
      {/* Panel header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          borderBottom: "1px solid #2A333B",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: "11px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#5A6472",
            fontFamily: "'IBM Plex Sans', sans-serif",
          }}
        >
          Node Detail
        </span>
        <button
          onClick={onClose}
          aria-label="Close node detail"
          style={{
            background: "none",
            border: "none",
            color: "#5A6472",
            cursor: "pointer",
            fontSize: "16px",
            lineHeight: 1,
            padding: "2px 4px",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "#E8ECEF"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "#5A6472"; }}
        >
          ×
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto" }}>
        {isLoading && <WidgetSkeleton rows={6} height={20} />}

        {isError && (
          <WidgetError title="Node detail unavailable" />
        )}

        {node && (
          <>
            {/* Identity block */}
            <div style={{ padding: "14px", borderBottom: "1px solid #2A333B" }}>
              {/* Type badge */}
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "2px 7px",
                  border: `1px solid ${colors.border}`,
                  borderRadius: "2px",
                  backgroundColor: colors.bg,
                  marginBottom: "10px",
                }}
              >
                <span
                  style={{
                    width: "5px",
                    height: "5px",
                    borderRadius: "1px",
                    backgroundColor: colors.border,
                    flexShrink: 0,
                  }}
                  aria-hidden="true"
                />
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: colors.text,
                    fontFamily: "'IBM Plex Sans', sans-serif",
                  }}
                >
                  {node.entity_type}
                </span>
              </div>

              {/* Name */}
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  color: "#E8ECEF",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  marginBottom: "12px",
                  wordBreak: "break-word",
                }}
              >
                {node.name}
              </div>

              {/* Properties table */}
              {[
                { label: "Entity ID",  value: node.entity_id },
                { label: "Confidence", value: node.confidence != null ? `${(node.confidence * 100).toFixed(0)}%` : "—" },
                { label: "Version",    value: node.extraction_version ?? "—" },
                { label: "Created",    value: node.created_at ? new Date(node.created_at).toLocaleDateString() : "—" },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "100px 1fr",
                    gap: "6px",
                    marginBottom: "4px",
                  }}
                >
                  <span
                    style={{
                      fontSize: "10px",
                      color: "#5A6472",
                      fontWeight: 600,
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                      fontFamily: "'IBM Plex Sans', sans-serif",
                    }}
                  >
                    {label}
                  </span>
                  <span
                    className="font-mono"
                    style={{ fontSize: "11px", color: "#8A96A3", wordBreak: "break-all" }}
                  >
                    {value}
                  </span>
                </div>
              ))}

              {/* Aliases */}
              {node.aliases && node.aliases.length > 0 && (
                <div style={{ marginTop: "8px" }}>
                  <span
                    style={{
                      fontSize: "10px",
                      color: "#5A6472",
                      fontWeight: 600,
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                      fontFamily: "'IBM Plex Sans', sans-serif",
                    }}
                  >
                    Aliases
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                    {node.aliases.map((alias) => (
                      <span
                        key={alias}
                        style={{
                          fontSize: "10px",
                          color: "#8A96A3",
                          border: "1px solid #2A333B",
                          borderRadius: "2px",
                          padding: "1px 5px",
                          fontFamily: "'IBM Plex Sans', sans-serif",
                        }}
                      >
                        {alias}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Neighbors table */}
            <div style={{ flexShrink: 0 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 14px",
                  borderBottom: "1px solid #2A333B",
                }}
              >
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 600,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "#5A6472",
                    fontFamily: "'IBM Plex Sans', sans-serif",
                  }}
                >
                  Relationships
                </span>
                <span className="font-mono" style={{ fontSize: "10px", color: "#3A4450" }}>
                  {neighbors.length}
                </span>
              </div>

              {neighbors.length === 0 && (
                <p
                  style={{
                    padding: "12px 14px",
                    fontSize: "11px",
                    color: "#5A6472",
                    fontFamily: "'IBM Plex Sans', sans-serif",
                  }}
                >
                  No relationships found.
                </p>
              )}

              {neighbors.map((n, i) => {
                const nc = ENTITY_COLORS[n.neighbor_label] ?? DEFAULT_COLOR;
                return (
                  <div
                    key={`${n.neighbor_id}-${i}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr auto",
                      alignItems: "center",
                      gap: "8px",
                      padding: "7px 14px",
                      borderBottom: "1px solid #2A333B",
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: "11px",
                          fontWeight: 500,
                          color: "#E8ECEF",
                          fontFamily: "'IBM Plex Sans', sans-serif",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {n.neighbor_name}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "4px", marginTop: "2px" }}>
                        <span
                          style={{
                            width: "5px",
                            height: "5px",
                            borderRadius: "1px",
                            backgroundColor: nc.border,
                            flexShrink: 0,
                          }}
                          aria-hidden="true"
                        />
                        <span
                          style={{
                            fontSize: "9px",
                            color: nc.text,
                            fontFamily: "'IBM Plex Sans', sans-serif",
                            textTransform: "uppercase",
                            letterSpacing: "0.04em",
                          }}
                        >
                          {n.neighbor_label}
                        </span>
                      </div>
                    </div>
                    <span
                      className="font-mono"
                      style={{
                        fontSize: "9px",
                        color: "#3DDBD9",
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                        flexShrink: 0,
                      }}
                    >
                      {n.relationship}
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}

// ─── Main page client ────────────────────────────────────────────────────────

const PAGE_SIZE = 50;

export function GraphPageClient() {
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Fetch paginated nodes
  const { data, isLoading, isError, refetch } = useQuery<NodesResponse>({
    queryKey: ["graph-nodes", page],
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/graph/nodes?page=${page}&limit=${PAGE_SIZE}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      return json.data as NodesResponse;
    },
    staleTime: 30_000,
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const pagination = data?.pagination;
  const totalPages = pagination ? Math.ceil(pagination.total / PAGE_SIZE) : 1;

  // Build ReactFlow nodes — memoized to avoid recreation on every render
  const flowNodes = useMemo(() => buildFlowNodes(items), [items]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Fetch node detail (lifted from DetailPanel)
  const { data: detailData, isLoading: detailLoading, isError: detailError } = useQuery<NodeDetailResponse>({
    queryKey: ["graph-node-detail", selectedId],
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/graph/node/${encodeURIComponent(selectedId!)}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      return json.data as NodeDetailResponse;
    },
    enabled: !!selectedId,
    staleTime: 60_000,
  });

  // Handle graph edges & neighbor nodes when detailData arrives
  useEffect(() => {
    if (!selectedId || !detailData) {
      setNodes(flowNodes);
      setEdges([]);
      return;
    }

    const neighbors = detailData.neighbors;
    const newEdges: Edge[] = [];
    const extraNodes: Node[] = [];
    const baseNodeIds = new Set(flowNodes.map((n) => n.id));
    
    // Find selected node position to layout extra nodes radially
    const selectedNode = flowNodes.find((n) => n.id === selectedId) || { position: { x: 200, y: 200 } };
    const cx = selectedNode.position.x;
    const cy = selectedNode.position.y;
    const radius = 220;

    neighbors.forEach((n, i) => {
      // Create edge
      newEdges.push({
        id: `${selectedId}-${n.neighbor_id}`,
        source: selectedId,
        target: n.neighbor_id,
        label: n.relationship,
        className: "graph-edge",
        style: { strokeWidth: 1.5 },
        labelStyle: { fill: "#3DDBD9", fontSize: 9, fontFamily: "'IBM Plex Sans', sans-serif" },
        labelBgStyle: { fill: "#151A1F" },
      });

      // Add missing neighbor nodes
      if (!baseNodeIds.has(n.neighbor_id)) {
        const angle = (i / neighbors.length) * 2 * Math.PI;
        const nx = cx + radius * Math.cos(angle);
        const ny = cy + radius * Math.sin(angle);
        const colors = ENTITY_COLORS[n.neighbor_label] ?? DEFAULT_COLOR;

        extraNodes.push({
          id: n.neighbor_id,
          position: { x: nx, y: ny },
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
                  {n.neighbor_label}
                </div>
                <div
                  style={{
                    fontSize: "11px",
                    fontWeight: 500,
                    color: "#E8ECEF",
                    maxWidth: "140px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    fontFamily: "'IBM Plex Sans', sans-serif",
                  }}
                >
                  {n.neighbor_name}
                </div>
              </div>
            ),
            entityLabel: n.neighbor_label,
          },
          style: {
            backgroundColor: colors.bg,
            border: `1px dashed ${colors.border}`,
            borderRadius: "2px",
            padding: "6px 10px",
            minWidth: "110px",
            cursor: "pointer",
            opacity: 0.85,
          },
        });
        baseNodeIds.add(n.neighbor_id);
      }
    });

    setNodes([...flowNodes, ...extraNodes]);
    setEdges(newEdges);
  }, [selectedId, detailData, flowNodes, setNodes, setEdges]);

  // Reset graph when pagination changes
  useEffect(() => {
    setNodes(flowNodes);
    setEdges([]);
    setSelectedId(null);
  }, [flowNodes, setNodes, setEdges]);

  const onNodeClick: NodeMouseHandler = useCallback((_evt, node) => {
    setSelectedId(node.id);
  }, []);

  const closePanel = useCallback(() => setSelectedId(null), []);

  return (
    <div
      style={{
        height: "calc(100vh - 48px)",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#0B0E11",
        fontFamily: "'IBM Plex Sans', sans-serif",
      }}
    >
      <style>{`
        .graph-edge .react-flow__edge-path {
          stroke: #3A4450;
          transition: stroke 0.2s;
        }
        .graph-edge:hover .react-flow__edge-path,
        .graph-edge.selected .react-flow__edge-path {
          stroke: #3DDBD9 !important;
        }
      `}</style>
      {/* ── Toolbar ─────────────────────────────────────────────────────── */}
      <div
        style={{
          height: "40px",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 16px",
          backgroundColor: "#151A1F",
          borderBottom: "1px solid #2A333B",
        }}
      >
        {/* Left: title + count */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#5A6472",
            }}
          >
            Knowledge Graph
          </span>
          {pagination && (
            <span className="font-mono" style={{ fontSize: "10px", color: "#3A4450" }}>
              {pagination.total} NODES · PAGE {page}/{totalPages}
            </span>
          )}
        </div>

        {/* Right: pagination */}
        {totalPages > 1 && (
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              style={{
                padding: "3px 10px",
                fontSize: "11px",
                fontFamily: "'IBM Plex Sans', sans-serif",
                color: page === 1 ? "#3A4450" : "#8A96A3",
                backgroundColor: "transparent",
                border: "1px solid #2A333B",
                borderRadius: "2px",
                cursor: page === 1 ? "not-allowed" : "pointer",
              }}
            >
              ← Prev
            </button>
            <span className="font-mono" style={{ fontSize: "10px", color: "#5A6472", minWidth: "60px", textAlign: "center" }}>
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              style={{
                padding: "3px 10px",
                fontSize: "11px",
                fontFamily: "'IBM Plex Sans', sans-serif",
                color: page === totalPages ? "#3A4450" : "#8A96A3",
                backgroundColor: "transparent",
                border: "1px solid #2A333B",
                borderRadius: "2px",
                cursor: page === totalPages ? "not-allowed" : "pointer",
              }}
            >
              Next →
            </button>
          </div>
        )}
      </div>

      {/* ── Main area ────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Canvas */}
        <div style={{ flex: 1, position: "relative" }}>
          {isLoading && (
            <div style={{ padding: "24px" }}>
              <WidgetSkeleton rows={10} height={16} />
            </div>
          )}

          {isError && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
              }}
            >
              <WidgetError
                title="Graph unavailable"
                message="Could not load graph nodes from the backend."
                onRetry={() => refetch()}
              />
            </div>
          )}

          {!isLoading && !isError && items.length === 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
              }}
            >
              <WidgetEmpty message="No entities in the knowledge graph yet. Upload and process documents to populate the graph." />
            </div>
          )}

          {!isLoading && !isError && items.length > 0 && (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={NODE_TYPES}
              edgeTypes={EDGE_TYPES}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              fitViewOptions={{ padding: 0.15 }}
              nodesDraggable
              nodesConnectable={false}
              elementsSelectable
              style={{ backgroundColor: "#0B0E11" }}
              aria-label="Knowledge Graph explorer"
            >
              <Background variant={BackgroundVariant.Dots} color="#2A333B" size={1} gap={20} />
              <Controls />
              <MiniMap
                style={{ backgroundColor: "#0B0E11", border: "1px solid #2A333B" }}
                nodeColor={(n) => {
                  const lbl = (n.data as { entityLabel?: string })?.entityLabel ?? "";
                  return (ENTITY_COLORS[lbl] ?? DEFAULT_COLOR).border;
                }}
                maskColor="rgba(11,14,17,0.7)"
              />
            </ReactFlow>
          )}
        </div>

        {/* Detail panel */}
        {selectedId && (
          <DetailPanel
            entityId={selectedId}
            data={detailData}
            isLoading={detailLoading}
            isError={detailError}
            onClose={closePanel}
          />
        )}
      </div>

      {/* ── Legend ──────────────────────────────────────────────────────── */}
      <div
        style={{
          flexShrink: 0,
          borderTop: "1px solid #2A333B",
          backgroundColor: "#0B0E11",
          padding: "6px 16px",
          display: "flex",
          flexWrap: "wrap",
          gap: "12px",
          alignItems: "center",
        }}
      >
        <span
          style={{
            fontSize: "9px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "#3A4450",
            marginRight: "4px",
          }}
        >
          Legend
        </span>
        {Object.entries(ENTITY_COLORS).map(([type, colors]) => (
          <div key={type} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
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
              style={{ fontSize: "10px", color: "#5A6472", fontFamily: "'IBM Plex Sans', sans-serif" }}
            >
              {type}
            </span>
          </div>
        ))}
        <span
          style={{
            marginLeft: "auto",
            fontSize: "10px",
            color: "#3A4450",
            fontFamily: "'IBM Plex Mono', monospace",
          }}
        >
          Click a node to inspect · Drag to reposition
        </span>
      </div>
    </div>
  );
}
