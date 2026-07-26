"use client";

/**
 * ActivityTimeline — Recent Activity Widget
 *
 * Chronological event list, newest first.
 * Signal-color icons matching event types.
 * IBM Plex Mono timestamps.
 */

import { useDashboardActivity } from "../hooks/use-dashboard";
import { WidgetSkeleton } from "./widget-skeleton";
import { WidgetError } from "./widget-error";
import { WidgetEmpty } from "./widget-empty";
import type { ActivityEvent } from "../types";

const EVENT_CONFIG: Record<string, { color: string; icon: string; label: string }> = {
  document_uploaded:     { color: "#3DDBD9", icon: "↑", label: "Uploaded" },
  processing_completed:  { color: "#4ADE80", icon: "✓", label: "Completed" },
  graph_updated:         { color: "#3DDBD9", icon: "◈", label: "Graph Updated" },
  embeddings_created:    { color: "#4ADE80", icon: "⬡", label: "Embedded" },
  asset_updated:         { color: "#F5A623", icon: "◉", label: "Asset Updated" },
  user_search:           { color: "#8A96A3", icon: "⌕", label: "Search" },
};

function getEventConfig(type: string) {
  return EVENT_CONFIG[type] ?? { color: "#8A96A3", icon: "·", label: type };
}

function timeStr(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return "—";
  }
}

function dateStr(isoStr: string): string {
  try {
    return new Date(isoStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

function EventRow({ event, showDate }: { event: ActivityEvent; showDate: boolean }) {
  const config = getEventConfig(event.event_type);

  return (
    <div
      className="hover-elevate"
      style={{
        display: "flex",
        gap: "10px",
        padding: "6px 14px",
        borderBottom: "1px solid #2A333B",
        alignItems: "flex-start",
      }}
    >
      {/* Timeline dot + connector */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          paddingTop: "3px",
          gap: "2px",
          flexShrink: 0,
        }}
        aria-hidden="true"
      >
        <span
          style={{
            width: "16px",
            height: "16px",
            borderRadius: "2px",
            backgroundColor: `${config.color}20`,
            border: `1px solid ${config.color}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "9px",
            color: config.color,
            fontWeight: 700,
          }}
        >
          {config.icon}
        </span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: "12px",
            fontWeight: 500,
            color: "#E8ECEF",
            fontFamily: "'IBM Plex Sans', sans-serif",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {event.detail}
        </div>
        {event.document_name && (
          <div
            style={{
              fontSize: "10px",
              color: "#8A96A3",
              fontFamily: "'IBM Plex Sans', sans-serif",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              marginTop: "1px",
            }}
          >
            {event.document_name}
          </div>
        )}
      </div>

      {/* Timestamp */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          gap: "2px",
          flexShrink: 0,
        }}
      >
        <span
          className="font-mono"
          style={{ fontSize: "10px", color: "#5A6472" }}
        >
          {timeStr(event.timestamp)}
        </span>
        {showDate && (
          <span
            className="font-mono"
            style={{ fontSize: "9px", color: "#3A4450" }}
          >
            {dateStr(event.timestamp)}
          </span>
        )}
      </div>
    </div>
  );
}

export function ActivityTimeline() {
  const { data, isLoading, isError, refetch } = useDashboardActivity();
  const events = data?.events ?? [];

  return (
    <div className="widget widget-reveal">
      <div className="widget-header">
        <span className="widget-title">Activity Timeline</span>
        {data && (
          <span className="font-mono" style={{ fontSize: "10px", color: "#5A6472" }}>
            {data.total} EVENTS
          </span>
        )}
      </div>

      {isLoading && <WidgetSkeleton rows={6} height={24} />}

      {isError && (
        <WidgetError
          title="Activity unavailable"
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && events.length === 0 && (
        <WidgetEmpty message="No activity recorded. Upload documents to see events." />
      )}

      {!isLoading && !isError && events.length > 0 && (
        <div style={{ maxHeight: "200px", overflowY: "auto" }}>
          {events.map((event, i) => {
            const prevEvent = events[i - 1];
            const showDate =
              i === 0 ||
              new Date(prevEvent.timestamp).toDateString() !==
                new Date(event.timestamp).toDateString();
            return (
              <EventRow
                key={`${event.event_type}-${event.timestamp}-${i}`}
                event={event}
                showDate={showDate}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
