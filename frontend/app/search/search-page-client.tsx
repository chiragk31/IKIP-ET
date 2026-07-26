"use client";

/**
 * SearchPageClient — Full-page Hybrid Search Interface
 *
 * Calls POST /api/v1/search with the real SearchRequest schema.
 * Types derived directly from backend/app/search/schemas.py + models.py
 * and verified against a live API call (2026-07-26).
 *
 * Request shape  (SearchRequest):
 *   { query, top_k, min_score, graph_depth, expand_graph, rerank,
 *     filters: { asset_id?, document_type?, ... } }
 *
 * Response shape (data field of the success_response wrapper):
 *   { query, total_results, chunks[], graph_nodes[], citations[], diagnostics }
 *
 * chunks[]:      { chunk_id, document_id, text, section, page_number, score,
 *                  graph_entities[], asset_ids[], document_type, language,
 *                  created_at, citation? }
 * citations[]:   { document_id, document_name, section, page_number, chunk_id,
 *                  asset_ids[], confidence, source_type }
 * graph_nodes[]: { node_id, node_name, node_label, relationship, seed_entity_id,
 *                  hop, properties }
 * diagnostics:   { duration_seconds, semantic_chunks, filtered_chunks,
 *                  graph_nodes_discovered, expanded_query }
 */

import { useCallback, useRef, useState } from "react";
import { WidgetError } from "@/features/dashboard/components/widget-error";
import { WidgetEmpty } from "@/features/dashboard/components/widget-empty";

// ─── Types (matched exactly to backend schemas) ───────────────────────────────

interface MetadataFilters {
  asset_id?: string;
  document_type?: string;
}

interface SearchRequest {
  query: string;
  top_k: number;
  min_score: number;
  expand_graph: boolean;
  rerank: boolean;
  filters: MetadataFilters;
}

interface Citation {
  document_id: string;
  document_name: string;
  section: string;
  page_number: number | null;
  chunk_id: string;
  asset_ids: string[];
  confidence: number;
  source_type: string;
}

interface ContextChunk {
  chunk_id: string;
  document_id: string;
  text: string;
  section: string;
  page_number: number | null;
  score: number;
  graph_entities: string[];
  asset_ids: string[];
  document_type: string;
  language: string;
  created_at: string;
  citation: Citation | null;
}

interface GraphExpansionNode {
  node_id: string;
  node_name: string;
  node_label: string;
  relationship: string;
  seed_entity_id: string;
  hop: number;
}

interface SearchDiagnostics {
  duration_seconds: number;
  semantic_chunks: number;
  filtered_chunks: number;
  graph_nodes_discovered: number;
  expanded_query: string;
}

interface SearchResponseData {
  query: string;
  total_results: number;
  chunks: ContextChunk[];
  graph_nodes: GraphExpansionNode[];
  citations: Citation[];
  diagnostics: SearchDiagnostics;
}

// ─── Entity type colors (reused from graph explorer) ─────────────────────────

const ENTITY_COLORS: Record<string, string> = {
  Asset:        "#F5A623",
  Failure:      "#E5484D",
  Person:       "#4ADE80",
  Location:     "#3DDBD9",
  Document:     "#8A96A3",
  Procedure:    "#3DDBD9",
  Measurement:  "#4ADE80",
  Risk:         "#F5A623",
  Regulation:   "#8A96A3",
  Organization: "#8A96A3",
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Sub-components ───────────────────────────────────────────────────────────

/** A single search result card */
function ChunkResult({ chunk, index }: { chunk: ContextChunk; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const score = chunk.score;
  const scoreColor =
    score >= 0.7 ? "#4ADE80" : score >= 0.5 ? "#F5A623" : "#8A96A3";

  const doc = chunk.citation?.document_name ?? chunk.document_id;
  const section = chunk.section || chunk.citation?.section || "";
  const page = chunk.page_number ?? chunk.citation?.page_number;

  // Truncate long text unless expanded
  const TRUNC = 280;
  const needsTrunc = chunk.text.length > TRUNC;
  const displayText = !expanded && needsTrunc
    ? chunk.text.slice(0, TRUNC) + "…"
    : chunk.text;

  return (
    <div
      style={{
        backgroundColor: "#151A1F",
        border: "1px solid #2A333B",
        borderRadius: "2px",
        marginBottom: "8px",
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "28px 1fr auto",
          alignItems: "center",
          gap: "10px",
          padding: "8px 14px",
          borderBottom: "1px solid #2A333B",
        }}
      >
        {/* Rank */}
        <span
          className="font-mono"
          style={{
            fontSize: "11px",
            color: "#3A4450",
            textAlign: "center",
          }}
        >
          {index + 1}
        </span>

        {/* Doc + section */}
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: "#E8ECEF",
              fontFamily: "'IBM Plex Sans', sans-serif",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {doc}
          </div>
          {(section || page != null) && (
            <div
              style={{
                fontSize: "10px",
                color: "#5A6472",
                fontFamily: "'IBM Plex Sans', sans-serif",
                marginTop: "1px",
              }}
            >
              {section}
              {page != null ? ` · p.${page}` : ""}
            </div>
          )}
        </div>

        {/* Confidence score */}
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <span
            className="font-mono"
            style={{ fontSize: "12px", fontWeight: 600, color: scoreColor }}
          >
            {(score * 100).toFixed(0)}%
          </span>
          <div
            style={{
              fontSize: "9px",
              color: "#3A4450",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              marginTop: "1px",
            }}
          >
            {chunk.citation?.source_type ?? "semantic"}
          </div>
        </div>
      </div>

      {/* Excerpt */}
      <div style={{ padding: "10px 14px 10px 52px" }}>
        <p
          style={{
            fontSize: "12px",
            lineHeight: 1.65,
            color: "#8A96A3",
            fontFamily: "'IBM Plex Sans', sans-serif",
            margin: 0,
          }}
        >
          {displayText}
        </p>
        {needsTrunc && (
          <button
            onClick={() => setExpanded((e) => !e)}
            style={{
              marginTop: "6px",
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "11px",
              color: "#3DDBD9",
              fontFamily: "'IBM Plex Sans', sans-serif",
              padding: 0,
            }}
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        )}
      </div>

      {/* Asset IDs / graph entities */}
      {chunk.asset_ids.length > 0 && (
        <div
          style={{
            padding: "6px 14px 6px 52px",
            borderTop: "1px solid #2A333B",
            display: "flex",
            flexWrap: "wrap",
            gap: "5px",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontSize: "9px",
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "#3A4450",
              marginRight: "2px",
              fontFamily: "'IBM Plex Sans', sans-serif",
            }}
          >
            Assets
          </span>
          {chunk.asset_ids.map((id) => (
            <span
              key={id}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "1px 6px",
                border: "1px solid #2A333B",
                borderRadius: "2px",
                fontSize: "10px",
                color: "#F5A623",
                fontFamily: "'IBM Plex Mono', monospace",
              }}
            >
              <span
                style={{
                  width: "5px",
                  height: "5px",
                  borderRadius: "1px",
                  backgroundColor: "#F5A623",
                  flexShrink: 0,
                }}
                aria-hidden="true"
              />
              {id}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Graph nodes discovered during graph expansion */
function GraphNodesSection({ nodes }: { nodes: GraphExpansionNode[] }) {
  if (nodes.length === 0) return null;
  return (
    <div
      style={{
        backgroundColor: "#151A1F",
        border: "1px solid #2A333B",
        borderRadius: "2px",
        marginBottom: "24px",
      }}
    >
      <div
        style={{
          padding: "8px 14px",
          borderBottom: "1px solid #2A333B",
          display: "flex",
          alignItems: "center",
          gap: "8px",
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
          Graph Expansion
        </span>
        <span className="font-mono" style={{ fontSize: "10px", color: "#3A4450" }}>
          {nodes.length} nodes
        </span>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", padding: "10px 14px" }}>
        {nodes.map((n) => {
          const color = ENTITY_COLORS[n.node_label] ?? "#8A96A3";
          return (
            <span
              key={n.node_id}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                padding: "2px 8px",
                border: `1px solid ${color}40`,
                borderRadius: "2px",
                backgroundColor: `${color}12`,
                fontSize: "11px",
                fontFamily: "'IBM Plex Sans', sans-serif",
              }}
            >
              <span
                style={{
                  width: "5px",
                  height: "5px",
                  borderRadius: "1px",
                  backgroundColor: color,
                  flexShrink: 0,
                }}
                aria-hidden="true"
              />
              <span style={{ color: "#E8ECEF" }}>{n.node_name}</span>
              <span
                className="font-mono"
                style={{ fontSize: "9px", color: "#5A6472", textTransform: "uppercase" }}
              >
                {n.relationship}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

/** Diagnostics footer bar */
function DiagnosticsBar({ d }: { d: SearchDiagnostics }) {
  return (
    <div
      style={{
        display: "flex",
        gap: "16px",
        flexWrap: "wrap",
        padding: "6px 0",
        borderTop: "1px solid #2A333B",
        marginTop: "16px",
      }}
    >
      {[
        ["Duration",  `${d.duration_seconds.toFixed(2)}s`],
        ["Chunks",    String(d.semantic_chunks)],
        ["Filtered",  String(d.filtered_chunks)],
        ["Graph",     String(d.graph_nodes_discovered)],
        ["Expanded",  d.expanded_query || "—"],
      ].map(([label, val]) => (
        <div key={label} style={{ display: "flex", gap: "5px", alignItems: "baseline" }}>
          <span
            style={{
              fontSize: "9px",
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "#3A4450",
              fontFamily: "'IBM Plex Sans', sans-serif",
            }}
          >
            {label}
          </span>
          <span className="font-mono" style={{ fontSize: "11px", color: "#5A6472" }}>
            {val}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

const DEFAULTS: SearchRequest = {
  query: "",
  top_k: 10,
  min_score: 0.3,
  expand_graph: false,
  rerank: true,
  filters: {},
};

export function SearchPageClient() {
  const [query, setQuery]           = useState("");
  const [assetFilter, setAssetFilter] = useState("");
  const [expandGraph, setExpandGraph] = useState(false);
  const [topK, setTopK]             = useState(10);

  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [result, setResult]     = useState<SearchResponseData | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = useCallback(async () => {
    const q = query.trim();
    if (q.length < 2) return;

    setLoading(true);
    setError(null);
    setHasSearched(true);

    const body: SearchRequest = {
      ...DEFAULTS,
      query: q,
      top_k: topK,
      expand_graph: expandGraph,
      filters: {
        ...(assetFilter.trim() ? { asset_id: assetFilter.trim() } : {}),
      },
    };

    try {
      const res = await fetch(`${API_BASE}/api/v1/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
      }
      const json = await res.json();
      setResult(json.data as SearchResponseData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [query, topK, expandGraph, assetFilter]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") handleSearch();
    },
    [handleSearch]
  );

  const isEmpty = result && result.total_results === 0;

  return (
    <div
      style={{
        minHeight: "calc(100vh - 48px)",
        backgroundColor: "#0B0E11",
        fontFamily: "'IBM Plex Sans', sans-serif",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* ── Search bar + controls ──────────────────────────────────────── */}
      <div
        style={{
          backgroundColor: "#151A1F",
          borderBottom: "1px solid #2A333B",
          padding: "16px 24px",
          flexShrink: 0,
        }}
      >
        {/* Main input */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            alignItems: "stretch",
            maxWidth: "900px",
          }}
        >
          <div style={{ flex: 1, position: "relative" }}>
            <input
              ref={inputRef}
              id="search-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question — e.g. What caused the pump seal failure?"
              aria-label="Search query"
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 14px",
                backgroundColor: "#0B0E11",
                border: "1px solid #2A333B",
                borderRadius: "2px",
                fontSize: "13px",
                color: "#E8ECEF",
                fontFamily: "'IBM Plex Sans', sans-serif",
                outline: "none",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "#F5A623"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "#2A333B"; }}
            />
          </div>

          <button
            id="search-submit-btn"
            onClick={handleSearch}
            disabled={loading || query.trim().length < 2}
            aria-label="Submit search"
            style={{
              padding: "10px 20px",
              backgroundColor: loading || query.trim().length < 2 ? "#2A333B" : "#F5A623",
              color: loading || query.trim().length < 2 ? "#5A6472" : "#0B0E11",
              border: "none",
              borderRadius: "2px",
              fontSize: "12px",
              fontWeight: 700,
              fontFamily: "'IBM Plex Sans', sans-serif",
              letterSpacing: "0.04em",
              cursor: loading || query.trim().length < 2 ? "not-allowed" : "pointer",
              transition: "background-color 0.15s",
              flexShrink: 0,
              whiteSpace: "nowrap",
            }}
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </div>

        {/* Filter controls */}
        <div
          style={{
            display: "flex",
            gap: "16px",
            flexWrap: "wrap",
            alignItems: "center",
            marginTop: "10px",
          }}
        >
          {/* Asset filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <label
              htmlFor="filter-asset"
              style={{
                fontSize: "10px",
                fontWeight: 600,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "#5A6472",
              }}
            >
              Asset
            </label>
            <input
              id="filter-asset"
              type="text"
              value={assetFilter}
              onChange={(e) => setAssetFilter(e.target.value)}
              placeholder="asset_p101"
              style={{
                padding: "4px 8px",
                backgroundColor: "#0B0E11",
                border: "1px solid #2A333B",
                borderRadius: "2px",
                fontSize: "11px",
                color: "#8A96A3",
                fontFamily: "'IBM Plex Mono', monospace",
                width: "130px",
                outline: "none",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "#3DDBD9"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "#2A333B"; }}
            />
          </div>

          {/* Top K */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <label
              htmlFor="filter-topk"
              style={{
                fontSize: "10px",
                fontWeight: 600,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "#5A6472",
              }}
            >
              Top K
            </label>
            <select
              id="filter-topk"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              style={{
                padding: "4px 8px",
                backgroundColor: "#0B0E11",
                border: "1px solid #2A333B",
                borderRadius: "2px",
                fontSize: "11px",
                color: "#8A96A3",
                fontFamily: "'IBM Plex Mono', monospace",
                outline: "none",
              }}
            >
              {[5, 10, 20, 50].map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>

          {/* Expand graph toggle */}
          <label
            htmlFor="filter-expand-graph"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              cursor: "pointer",
              fontSize: "11px",
              color: "#5A6472",
              userSelect: "none",
            }}
          >
            <input
              id="filter-expand-graph"
              type="checkbox"
              checked={expandGraph}
              onChange={(e) => setExpandGraph(e.target.checked)}
              style={{ accentColor: "#3DDBD9", width: "13px", height: "13px" }}
            />
            <span>Graph expansion</span>
            <span style={{ fontSize: "9px", color: "#3A4450" }}>(slower · ~25s)</span>
          </label>

          {/* Search duration hint */}
          <span
            style={{
              marginLeft: "auto",
              fontSize: "9px",
              color: "#3A4450",
              fontFamily: "'IBM Plex Mono', monospace",
            }}
          >
            {loading ? "⏳ searching… this can take 8–25s" : ""}
          </span>
        </div>
      </div>

      {/* ── Results area ──────────────────────────────────────────────────── */}
      <div style={{ flex: 1, padding: "20px 24px", maxWidth: "960px", width: "100%" }}>

        {/* Loading state */}
        {loading && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              paddingTop: "80px",
              gap: "12px",
            }}
            aria-live="polite"
            aria-label="Searching"
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                border: "2px solid #2A333B",
                borderTop: "2px solid #F5A623",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }}
            />
            <span style={{ fontSize: "13px", color: "#5A6472" }}>
              Searching knowledge base…
            </span>
            <span style={{ fontSize: "11px", color: "#3A4450", fontFamily: "'IBM Plex Mono', monospace" }}>
              Embedding → Pinecone → Graph{expandGraph ? " expansion" : ""} → Reranking
            </span>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <WidgetError
            title="Search failed"
            message={error}
            onRetry={handleSearch}
          />
        )}

        {/* Pre-search prompt */}
        {!loading && !error && !hasSearched && (
          <div
            style={{
              paddingTop: "60px",
              textAlign: "center",
              color: "#3A4450",
            }}
          >
            <div style={{ fontSize: "32px", marginBottom: "16px" }} aria-hidden="true">
              🔍
            </div>
            <p style={{ fontSize: "14px", color: "#5A6472", marginBottom: "8px" }}>
              Ask anything about your industrial knowledge base
            </p>
            <p style={{ fontSize: "11px", color: "#3A4450", fontFamily: "'IBM Plex Mono', monospace" }}>
              Try: &quot;What caused the pump seal failure?&quot; · &quot;P-101 maintenance history&quot; · &quot;ASME compliance requirements&quot;
            </p>
          </div>
        )}

        {/* Empty results */}
        {!loading && !error && isEmpty && (
          <WidgetEmpty
            message={`No results found for "${result!.query}". Try a broader query or lower the min_score filter.`}
          />
        )}

        {/* Results */}
        {!loading && !error && result && !isEmpty && (
          <>
            {/* Result summary bar */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                marginBottom: "16px",
              }}
            >
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                  color: "#5A6472",
                }}
              >
                Results
              </span>
              <span className="font-mono" style={{ fontSize: "11px", color: "#8A96A3" }}>
                {result.total_results} chunk{result.total_results !== 1 ? "s" : ""}
              </span>
              {result.citations.length > 0 && (
                <span className="font-mono" style={{ fontSize: "11px", color: "#3DDBD9" }}>
                  {result.citations.length} citation{result.citations.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>

            {/* Graph expansion nodes */}
            <GraphNodesSection nodes={result.graph_nodes} />

            {/* Chunk results */}
            <div role="list" aria-label="Search results">
              {result.chunks.map((chunk, i) => (
                <div role="listitem" key={chunk.chunk_id}>
                  <ChunkResult chunk={chunk} index={i} />
                </div>
              ))}
            </div>

            {/* Diagnostics */}
            <DiagnosticsBar d={result.diagnostics} />
          </>
        )}
      </div>
    </div>
  );
}
