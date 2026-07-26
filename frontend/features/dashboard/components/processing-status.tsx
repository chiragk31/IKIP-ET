"use client";

/**
 * ProcessingStatus — 7-Stage Pipeline Widget
 *
 * Horizontal stepper matching the real pipeline:
 *   Uploaded → Processing → Extraction → Ontology → Graph → Embeddings → Ready
 *
 * Visual language matches the Knowledge Pulse strip.
 * Each stage: small square node + thin connecting line.
 * Shows status, count, and per-stage timestamp where available.
 */

import { useDashboardDocuments } from "../hooks/use-dashboard";
import { WidgetSkeleton } from "./widget-skeleton";
import { WidgetError } from "./widget-error";
import type { DashboardDocument } from "../types";

const PIPELINE_STAGES = [
  { key: "uploaded",    label: "Uploaded",    short: "UPL" },
  { key: "processing",  label: "Processing",  short: "PROC" },
  { key: "extracting",  label: "Extraction",  short: "EXTR" },
  { key: "ontology",    label: "Ontology",    short: "ONTO" },
  { key: "graph",       label: "Graph",       short: "GRP" },
  { key: "embeddings",  label: "Embeddings",  short: "EMB" },
  { key: "completed",   label: "Ready",       short: "RDY" },
] as const;

// Map backend status/stage values to pipeline stage keys
function docToStageIndex(doc: DashboardDocument): number {
  const stage = doc.processing_stage ?? doc.status;
  if (!stage) return 0;
  if (stage.includes("embed") || stage === "generating_embeddings") return 5;
  if (stage.includes("graph") || stage === "building_graph") return 4;
  if (stage.includes("ontolog")) return 3;
  if (stage.includes("extract") || stage === "extracting") return 2;
  if (stage === "processing" || stage === "parsing" || stage === "ocr_running" || stage === "normalizing") return 1;
  if (stage === "completed") return 6;
  return 0;
}

function stageCount(docs: DashboardDocument[], stageIdx: number): number {
  return docs.filter((d) => docToStageIndex(d) === stageIdx).length;
}

export function ProcessingStatus() {
  const { data, isLoading, isError, refetch } = useDashboardDocuments();

  const docs = data?.documents ?? [];

  const counts = PIPELINE_STAGES.map((s, i) => stageCount(docs, i));
  const failedCount = docs.filter((d) => d.status === "failed").length;
  const total = data?.total ?? 0;

  return (
    <div className="widget widget-reveal" style={{ height: "100%" }}>
      <div className="widget-header">
        <span className="widget-title">Processing Pipeline</span>
        {!isLoading && (
          <span className="font-mono" style={{ fontSize: "10px", color: "#5A6472" }}>
            {total} DOCS
          </span>
        )}
      </div>

      <div style={{ padding: "16px 14px" }}>
        {isLoading && <WidgetSkeleton rows={3} height={10} />}

        {isError && (
          <WidgetError
            title="Pipeline status unavailable"
            onRetry={() => refetch()}
          />
        )}

        {!isLoading && !isError && (
          <>
            {/* Pipeline stepper */}
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 0,
                overflowX: "auto",
                paddingBottom: "4px",
              }}
              role="list"
              aria-label="Processing pipeline stages"
            >
              {PIPELINE_STAGES.map((stage, i) => {
                const count = counts[i];
                const isActive = count > 0;
                const isCompleted = stage.key === "completed";
                const isLast = i === PIPELINE_STAGES.length - 1;

                let nodeColor = "#2A333B";
                let labelColor = "#5A6472";
                if (isActive && isCompleted) {
                  nodeColor = "#4ADE80";
                  labelColor = "#4ADE80";
                } else if (isActive) {
                  nodeColor = "#3DDBD9";
                  labelColor = "#3DDBD9";
                }

                return (
                  <div
                    key={stage.key}
                    style={{ display: "flex", alignItems: "center", flex: "1 1 0" }}
                    role="listitem"
                  >
                    {/* Stage node */}
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px", flex: "0 0 auto" }}>
                      <div
                        style={{
                          width: "10px",
                          height: "10px",
                          borderRadius: "1px",
                          backgroundColor: nodeColor,
                          boxShadow: isActive ? `0 0 6px ${nodeColor}` : "none",
                          transition: "background-color 0.3s, box-shadow 0.3s",
                        }}
                        aria-label={`${stage.label}: ${count} documents`}
                      />
                      <span
                        style={{
                          fontSize: "8px",
                          fontWeight: 600,
                          letterSpacing: "0.06em",
                          textTransform: "uppercase",
                          color: labelColor,
                          fontFamily: "'IBM Plex Sans', sans-serif",
                          whiteSpace: "nowrap",
                          transition: "color 0.3s",
                        }}
                      >
                        {stage.short}
                      </span>
                      {isActive && (
                        <span
                          className="font-mono"
                          style={{
                            fontSize: "10px",
                            fontWeight: 600,
                            color: nodeColor,
                          }}
                        >
                          {count}
                        </span>
                      )}
                    </div>

                    {/* Connector line */}
                    {!isLast && (
                      <div
                        style={{
                          flex: 1,
                          height: "1px",
                          backgroundColor: "#2A333B",
                          marginTop: "-14px",
                        }}
                        aria-hidden="true"
                      />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Failed count if any */}
            {failedCount > 0 && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  marginTop: "12px",
                  padding: "6px 10px",
                  backgroundColor: "rgba(229, 72, 77, 0.08)",
                  border: "1px solid rgba(229, 72, 77, 0.2)",
                  borderRadius: "2px",
                }}
              >
                <span
                  className="status-sq failed"
                  aria-hidden="true"
                />
                <span
                  className="font-mono"
                  style={{ fontSize: "11px", color: "#E5484D" }}
                >
                  {failedCount} document{failedCount !== 1 ? "s" : ""} failed — review required
                </span>
              </div>
            )}

            {/* Recent docs in processing */}
            {docs.filter(d => d.status === "processing").length > 0 && (
              <div style={{ marginTop: "14px" }}>
                <div
                  style={{
                    fontSize: "10px",
                    fontWeight: 600,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "#5A6472",
                    marginBottom: "8px",
                    fontFamily: "'IBM Plex Sans', sans-serif",
                  }}
                >
                  Currently Processing
                </div>
                {docs
                  .filter(d => d.status === "processing")
                  .slice(0, 3)
                  .map((doc) => (
                    <div
                      key={doc.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        padding: "4px 0",
                        borderBottom: "1px solid #2A333B",
                      }}
                    >
                      <span
                        style={{
                          width: "5px",
                          height: "5px",
                          borderRadius: "1px",
                          backgroundColor: "#3DDBD9",
                          boxShadow: "0 0 4px #3DDBD9",
                          flexShrink: 0,
                        }}
                      />
                      <span
                        style={{
                          fontSize: "12px",
                          color: "#E8ECEF",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          flex: 1,
                          fontFamily: "'IBM Plex Sans', sans-serif",
                        }}
                      >
                        {doc.filename}
                      </span>
                      <span
                        style={{
                          fontSize: "10px",
                          color: "#3DDBD9",
                          fontFamily: "'IBM Plex Sans', sans-serif",
                          textTransform: "uppercase",
                          flexShrink: 0,
                        }}
                      >
                        {doc.processing_stage ?? "processing"}
                      </span>
                    </div>
                  ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
