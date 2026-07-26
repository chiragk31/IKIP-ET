"use client";

/**
 * SearchAnalytics — Search Analytics Widget
 *
 * Displays search activity using Recharts.
 * Signal color palette — no default Recharts colors.
 * Shows placeholder when no analytics backend exists yet.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useDashboardSearch } from "../hooks/use-dashboard";
import { WidgetSkeleton } from "./widget-skeleton";
import { WidgetError } from "./widget-error";
import { WidgetEmpty } from "./widget-empty";

const PLACEHOLDER_DATA = [
  { label: "Mon", value: 0 },
  { label: "Tue", value: 0 },
  { label: "Wed", value: 0 },
  { label: "Thu", value: 0 },
  { label: "Fri", value: 0 },
  { label: "Sat", value: 0 },
  { label: "Sun", value: 0 },
];

const CHART_STYLE = {
  fontSize: "10px",
  fontFamily: "'IBM Plex Mono', monospace",
  fill: "#8A96A3",
};

export function SearchAnalytics() {
  const { data, isLoading, isError, refetch } = useDashboardSearch();

  const chartData =
    data?.top_queries && data.top_queries.length > 0
      ? data.top_queries.map((q) => ({ label: q.query.slice(0, 12), value: q.count }))
      : PLACEHOLDER_DATA;

  const hasRealData = data?.total_searches ?? 0 > 0;

  return (
    <div className="widget widget-reveal" style={{ height: "100%" }}>
      <div className="widget-header">
        <span className="widget-title">Search Analytics</span>
        {data && (
          <span className="font-mono" style={{ fontSize: "10px", color: "#5A6472" }}>
            {data.total_searches} QUERIES
          </span>
        )}
      </div>

      <div style={{ padding: "14px" }}>
        {isLoading && <WidgetSkeleton rows={5} height={12} />}

        {isError && (
          <WidgetError
            title="Search analytics unavailable"
            onRetry={() => refetch()}
          />
        )}

        {!isLoading && !isError && (
          <>
            {/* Metrics row */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1px",
                backgroundColor: "#2A333B",
                marginBottom: "16px",
              }}
            >
              {[
                { label: "Total Searches", value: data?.total_searches ?? 0 },
                { label: "Avg Response", value: data?.avg_response_ms ? `${data.avg_response_ms}ms` : "—" },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    backgroundColor: "#151A1F",
                    padding: "10px 12px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "9px",
                      fontWeight: 600,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      color: "#5A6472",
                      fontFamily: "'IBM Plex Sans', sans-serif",
                      marginBottom: "4px",
                    }}
                  >
                    {m.label}
                  </div>
                  <div
                    className="font-mono"
                    style={{
                      fontSize: "18px",
                      fontWeight: 600,
                      color: "#E8ECEF",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {m.value}
                  </div>
                </div>
              ))}
            </div>

            {/* Chart */}
            {!hasRealData ? (
              <WidgetEmpty message="No search activity available. Analytics will appear after users run searches." />
            ) : (
              <div style={{ height: "120px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartData}
                    margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
                  >
                    <XAxis dataKey="label" tick={CHART_STYLE} axisLine={false} tickLine={false} />
                    <YAxis tick={CHART_STYLE} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1D242B",
                        border: "1px solid #2A333B",
                        borderRadius: "2px",
                        fontSize: "11px",
                        fontFamily: "'IBM Plex Mono', monospace",
                        color: "#E8ECEF",
                      }}
                      cursor={{ fill: "rgba(61, 219, 217, 0.05)" }}
                    />
                    <Bar dataKey="value" radius={[1, 1, 0, 0]}>
                      {chartData.map((_, i) => (
                        <Cell
                          key={i}
                          fill={i === chartData.length - 1 ? "#3DDBD9" : "#2A333B"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {data?.note && (
              <p
                style={{
                  marginTop: "8px",
                  fontSize: "10px",
                  color: "#5A6472",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                }}
              >
                {data.note}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
