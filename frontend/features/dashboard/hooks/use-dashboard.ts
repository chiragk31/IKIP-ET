/**
 * Dashboard TanStack Query Hooks
 *
 * One hook per widget — each independently fetches, caches, and refetches.
 * One widget failing NEVER blocks another.
 *
 * Refetch intervals:
 * - Overview: 30s (KPIs)
 * - Documents: 30s (upload status changes)
 * - Assets: 60s (relatively stable)
 * - System: 15s (health checks frequent)
 * - Graph: 60s (graph rarely changes)
 * - Activity: 20s (events stream)
 * - Search: 60s (analytics)
 */

import { useQuery } from "@tanstack/react-query";
import { DashboardService } from "../services/dashboard-service";

// --- Query Keys (stable identifiers for cache) ---
export const DASHBOARD_KEYS = {
  all: ["dashboard"] as const,
  overview: () => ["dashboard", "overview"] as const,
  documents: () => ["dashboard", "documents"] as const,
  assets: () => ["dashboard", "assets"] as const,
  system: () => ["dashboard", "system"] as const,
  graph: () => ["dashboard", "graph"] as const,
  activity: () => ["dashboard", "activity"] as const,
  search: () => ["dashboard", "search"] as const,
};

// -----------------------------------------------
// Overview Hook
// -----------------------------------------------
export function useDashboardOverview() {
  return useQuery({
    queryKey: DASHBOARD_KEYS.overview(),
    queryFn: DashboardService.getOverview,
    refetchInterval: 30_000,
    retry: 2,
    staleTime: 10_000,
  });
}

// -----------------------------------------------
// Documents Hook
// -----------------------------------------------
export function useDashboardDocuments() {
  return useQuery({
    queryKey: DASHBOARD_KEYS.documents(),
    queryFn: DashboardService.getDocuments,
    refetchInterval: 30_000,
    retry: 2,
    staleTime: 10_000,
  });
}

// -----------------------------------------------
// Assets Hook
// -----------------------------------------------
export function useDashboardAssets() {
  return useQuery({
    queryKey: DASHBOARD_KEYS.assets(),
    queryFn: DashboardService.getAssets,
    refetchInterval: 60_000,
    retry: 2,
    staleTime: 30_000,
  });
}

// -----------------------------------------------
// System Health Hook
// -----------------------------------------------
export function useDashboardSystem() {
  return useQuery({
    queryKey: DASHBOARD_KEYS.system(),
    queryFn: DashboardService.getSystem,
    refetchInterval: 15_000,
    retry: 1,
    staleTime: 5_000,
  });
}

// -----------------------------------------------
// Knowledge Graph Hook
// -----------------------------------------------
export function useDashboardGraph() {
  return useQuery({
    queryKey: DASHBOARD_KEYS.graph(),
    queryFn: DashboardService.getGraph,
    refetchInterval: 60_000,
    retry: 2,
    staleTime: 30_000,
  });
}

// -----------------------------------------------
// Activity Timeline Hook
// -----------------------------------------------
export function useDashboardActivity() {
  return useQuery({
    queryKey: DASHBOARD_KEYS.activity(),
    queryFn: DashboardService.getActivity,
    refetchInterval: 20_000,
    retry: 2,
    staleTime: 10_000,
  });
}

// -----------------------------------------------
// Search Analytics Hook
// -----------------------------------------------
export function useDashboardSearch() {
  return useQuery({
    queryKey: DASHBOARD_KEYS.search(),
    queryFn: DashboardService.getSearch,
    refetchInterval: 60_000,
    retry: 2,
    staleTime: 30_000,
  });
}
