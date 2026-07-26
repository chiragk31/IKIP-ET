/**
 * DashboardService
 *
 * All API calls for the Dashboard module.
 * Only calls /dashboard/* endpoints — thin aggregation layer on the backend.
 *
 * Rules:
 * - Never call fetch/axios directly from components
 * - Use apiGet from @/services/api
 * - Each method maps to exactly one backend endpoint
 */

import { apiGet } from "@/services/api";
import type {
  DashboardOverview,
  DashboardDocumentsData,
  DashboardAssetsData,
  DashboardSystemData,
  DashboardGraphData,
  DashboardActivityData,
  DashboardSearchData,
} from "../types";

export class DashboardService {
  /**
   * Fetch aggregated platform KPIs.
   * Maps to GET /dashboard/overview
   */
  static async getOverview(): Promise<DashboardOverview> {
    const res = await apiGet<DashboardOverview>("/dashboard/overview");
    if (!res.data) throw new Error(res.message || "No overview data");
    return res.data;
  }

  /**
   * Fetch recent documents for dashboard.
   * Maps to GET /dashboard/documents
   */
  static async getDocuments(): Promise<DashboardDocumentsData> {
    const res = await apiGet<DashboardDocumentsData>("/dashboard/documents");
    if (!res.data) throw new Error(res.message || "No documents data");
    return res.data;
  }

  /**
   * Fetch asset list for dashboard.
   * Maps to GET /dashboard/assets
   */
  static async getAssets(): Promise<DashboardAssetsData> {
    const res = await apiGet<DashboardAssetsData>("/dashboard/assets");
    if (!res.data) throw new Error(res.message || "No assets data");
    return res.data;
  }

  /**
   * Fetch system health for dashboard.
   * Maps to GET /dashboard/system
   */
  static async getSystem(): Promise<DashboardSystemData> {
    const res = await apiGet<DashboardSystemData>("/dashboard/system");
    if (!res.data) throw new Error(res.message || "No system data");
    return res.data;
  }

  /**
   * Fetch knowledge graph nodes for dashboard widget.
   * Maps to GET /dashboard/graph
   */
  static async getGraph(): Promise<DashboardGraphData> {
    const res = await apiGet<DashboardGraphData>("/dashboard/graph");
    if (!res.data) throw new Error(res.message || "No graph data");
    return res.data;
  }

  /**
   * Fetch activity timeline.
   * Maps to GET /dashboard/activity
   */
  static async getActivity(): Promise<DashboardActivityData> {
    const res = await apiGet<DashboardActivityData>("/dashboard/activity");
    if (!res.data) throw new Error(res.message || "No activity data");
    return res.data;
  }

  /**
   * Fetch search analytics.
   * Maps to GET /dashboard/search
   */
  static async getSearch(): Promise<DashboardSearchData> {
    const res = await apiGet<DashboardSearchData>("/dashboard/search");
    if (!res.data) throw new Error(res.message || "No search data");
    return res.data;
  }
}
