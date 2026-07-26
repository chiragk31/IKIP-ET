"use client";

/**
 * KnowledgePulse — Signature live strip
 *
 * The single continuously animated element on the dashboard.
 * Visualizes documents moving through the 7-stage pipeline:
 *   Uploaded → Processing → Extraction → Ontology → Graph → Embeddings → Ready
 *
 * Canvas-based particle flow animation. --signal-cyan for in-flight stages.
 * --signal-amber for warnings. Pure CSS + Canvas, no external animation library.
 */

import { useEffect, useRef } from "react";
import type { DashboardDocumentCounts } from "../types";

const STAGES = [
  { key: "uploaded",   label: "UPLOADED",   short: "UPL" },
  { key: "processing", label: "PROCESSING", short: "PROC" },
  { key: "extraction", label: "EXTRACTION", short: "EXTR" },
  { key: "ontology",   label: "ONTOLOGY",   short: "ONTO" },
  { key: "graph",      label: "GRAPH",      short: "GRP" },
  { key: "embeddings", label: "EMBEDDINGS", short: "EMB" },
  { key: "ready",      label: "READY",      short: "RDY" },
] as const;

interface Dot {
  stageIdx: number;
  x: number;
  y: number;
  speed: number;
  size: number;
  color: string;
  alpha: number;
}

interface KnowledgePulseProps {
  counts?: DashboardDocumentCounts;
}

export function KnowledgePulse({ counts }: KnowledgePulseProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const dotsRef = useRef<Dot[]>([]);

  const stageActivity: Record<string, number> = {
    uploaded:   counts?.queued ?? 0,
    processing: counts?.processing ?? 0,
    extraction: counts?.processing ?? 0,
    ontology:   counts?.processing ?? 0,
    graph:      counts?.processing ?? 0,
    embeddings: counts?.processing ?? 0,
    ready:      counts?.completed ?? 0,
  };
  const hasWarnings = (counts?.failed ?? 0) > 0;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas == null) return;

    const getCtx = (): CanvasRenderingContext2D | null =>
      canvas.getContext("2d");

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const spawnDot = (stageIdx: number, warn: boolean): Dot => {
      const w = canvas.width;
      const segW = w / STAGES.length;
      return {
        stageIdx,
        x: segW * stageIdx + Math.random() * segW * 0.3,
        y: canvas.height / 2 + (Math.random() - 0.5) * 6,
        speed: 0.8 + Math.random() * 1.2,
        size: 2 + Math.random() * 1.5,
        color: warn ? "#F5A623" : "#3DDBD9",
        alpha: 0,
      };
    };

    const updateDot = (d: Dot): void => {
      d.x += d.speed;
      const segW = canvas.width / STAGES.length;
      const progress = (d.x - segW * d.stageIdx) / segW;
      d.alpha = Math.min(1, progress * 5) * Math.min(1, (1 - progress) * 5);
    };

    const isDead = (d: Dot): boolean => {
      const segW = canvas.width / STAGES.length;
      return d.x > segW * (d.stageIdx + 1);
    };

    const drawDot = (ctx: CanvasRenderingContext2D, d: Dot): void => {
      ctx.save();
      ctx.globalAlpha = d.alpha * 0.9;
      ctx.fillStyle = d.color;
      ctx.shadowColor = d.color;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    };

    let frame = 0;
    const animate = () => {
      const ctx = getCtx();
      if (ctx == null) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Stage separator lines
      const segW = canvas.width / STAGES.length;
      ctx.strokeStyle = "#2A333B";
      ctx.lineWidth = 1;
      for (let i = 1; i < STAGES.length; i++) {
        ctx.beginPath();
        ctx.moveTo(segW * i, 0);
        ctx.lineTo(segW * i, canvas.height);
        ctx.stroke();
      }

      // Spawn particles
      if (frame % 8 === 0) {
        const stageIdx = Math.floor(Math.random() * STAGES.length);
        const stageKey = STAGES[stageIdx].key;
        if (stageActivity[stageKey] > 0 || Math.random() < 0.25) {
          const warn = hasWarnings && Math.random() < 0.2;
          dotsRef.current.push(spawnDot(stageIdx, warn));
        }
      }

      // Update / draw / cull
      const alive: Dot[] = [];
      for (const d of dotsRef.current) {
        updateDot(d);
        if (!isDead(d)) {
          drawDot(ctx, d);
          alive.push(d);
        }
      }
      dotsRef.current = alive.length > 80 ? alive.slice(-80) : alive;

      frame++;
      animRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animRef.current);
      ro.disconnect();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(stageActivity), hasWarnings]);

  return (
    <div
      aria-label="Knowledge Pipeline Status"
      style={{
        backgroundColor: "#0B0E11",
        borderBottom: "1px solid #2A333B",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Stage labels */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${STAGES.length}, 1fr)`,
          padding: "6px 0 0",
          position: "relative",
          zIndex: 1,
        }}
      >
        {STAGES.map((stage, i) => {
          const active = stageActivity[stage.key] > 0;
          const isReady = stage.key === "ready";
          const isLast = i === STAGES.length - 1;
          return (
            <div
              key={stage.key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "0 8px",
                borderRight: isLast ? "none" : "1px solid #2A333B",
              }}
            >
              <span
                style={{
                  width: "5px",
                  height: "5px",
                  borderRadius: "1px",
                  flexShrink: 0,
                  backgroundColor: active
                    ? "#3DDBD9"
                    : isReady && (counts?.completed ?? 0) > 0
                    ? "#4ADE80"
                    : "#2A333B",
                  boxShadow: active ? "0 0 4px #3DDBD9" : "none",
                  transition: "background-color 0.3s",
                }}
              />
              <span
                style={{
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  fontSize: "9px",
                  fontWeight: 600,
                  letterSpacing: "0.08em",
                  color: active ? "#E8ECEF" : "#5A6472",
                  textTransform: "uppercase" as const,
                  whiteSpace: "nowrap" as const,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {stage.label}
              </span>
              {active && (
                <span
                  className="font-mono"
                  style={{
                    fontSize: "9px",
                    color: "#3DDBD9",
                    marginLeft: "auto",
                  }}
                >
                  {stageActivity[stage.key]}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Canvas for particles */}
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        style={{
          display: "block",
          width: "100%",
          height: "32px",
          pointerEvents: "none",
        }}
      />

      {/* Warning badge */}
      {hasWarnings && (
        <div
          style={{
            position: "absolute",
            right: "12px",
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            alignItems: "center",
            gap: "4px",
            fontSize: "9px",
            fontWeight: 600,
            color: "#F5A623",
            letterSpacing: "0.06em",
            backgroundColor: "rgba(245, 166, 35, 0.1)",
            border: "1px solid rgba(245, 166, 35, 0.3)",
            padding: "2px 6px",
            borderRadius: "2px",
          }}
        >
          ⚠ {counts?.failed} FAILED
        </div>
      )}
    </div>
  );
}
