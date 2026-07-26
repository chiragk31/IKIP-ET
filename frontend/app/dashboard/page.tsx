import type { Metadata } from "next";
import { DashboardPageClient } from "./dashboard-page-client";

export const metadata: Metadata = {
  title: "Dashboard",
  description:
    "IKIP operational dashboard — overview of industrial knowledge assets, document processing pipeline, knowledge graph, and system health.",
};

export default function DashboardPage() {
  return <DashboardPageClient />;
}
