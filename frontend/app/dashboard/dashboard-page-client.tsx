"use client";

/**
 * DashboardPageClient — Dashboard Main Layout (Client)
 *
 * Assembles all widgets in a 12-column widescreen grid.
 * Each widget loads independently — one failure never blocks others.
 *
 * Layout (desktop ≥1280px):
 *   Header (full width)
 *   Knowledge Pulse (full width)
 *   KPI Cards (12 cols)
 *   Asset Intelligence (5) | Processing Pipeline (7)
 *   Knowledge Graph (8) | Search Analytics (4)
 *   Recent Documents (6) | System Health (6)
 *   Activity Timeline (12)
 */

import { useDashboardOverview } from "@/features/dashboard/hooks/use-dashboard";

import { KnowledgePulse } from "@/features/dashboard/components/knowledge-pulse";
import { OverviewCards } from "@/features/dashboard/components/overview-cards";
import { AssetIntelligence } from "@/features/dashboard/components/asset-intelligence";
import { ProcessingStatus } from "@/features/dashboard/components/processing-status";
import { KnowledgeGraphWidget } from "@/features/dashboard/components/knowledge-graph-widget";
import { SearchAnalytics } from "@/features/dashboard/components/search-analytics";
import { RecentDocuments } from "@/features/dashboard/components/recent-documents";
import { SystemHealth } from "@/features/dashboard/components/system-health";
import { ActivityTimeline } from "@/features/dashboard/components/activity-timeline";

export function DashboardPageClient() {
  const { data: overview } = useDashboardOverview();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "calc(100vh - 48px)",
        backgroundColor: "#0B0E11",
      }}
    >
      {/* Knowledge Pulse — signature animated strip */}
      <KnowledgePulse counts={overview?.documents} />

      {/* Main content */}
      <main
        style={{
          flex: 1,
          padding: "1px",
          backgroundColor: "#2A333B",
          display: "flex",
          flexDirection: "column",
          gap: "1px",
        }}
        id="dashboard-main"
        aria-label="Dashboard main content"
      >
        {/* Row 1: KPI Overview Cards (7 columns — full width) */}
        <section aria-label="Platform overview metrics">
          <OverviewCards />
        </section>

        {/* Row 2: Asset Intelligence (5/12) | Processing Pipeline (7/12) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "5fr 7fr",
            gap: "1px",
            backgroundColor: "#2A333B",
          }}
        >
          <section aria-label="Asset Intelligence">
            <AssetIntelligence />
          </section>
          <section aria-label="Processing Pipeline">
            <ProcessingStatus />
          </section>
        </div>

        {/* Row 3: Knowledge Graph (8/12) | Search Analytics (4/12) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "8fr 4fr",
            gap: "1px",
            backgroundColor: "#2A333B",
          }}
        >
          <section aria-label="Knowledge Graph">
            <KnowledgeGraphWidget />
          </section>
          <section aria-label="Search Analytics">
            <SearchAnalytics />
          </section>
        </div>

        {/* Row 4: Recent Documents (6/12) | System Health (6/12) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "1px",
            backgroundColor: "#2A333B",
          }}
        >
          <section aria-label="Recent Documents">
            <RecentDocuments />
          </section>
          <section aria-label="System Health">
            <SystemHealth />
          </section>
        </div>

        {/* Row 5: Activity Timeline (full width) */}
        <section aria-label="Activity Timeline">
          <ActivityTimeline />
        </section>
      </main>
    </div>
  );
}
