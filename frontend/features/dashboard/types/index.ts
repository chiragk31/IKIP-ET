/**
 * Dashboard Feature — TypeScript Types
 *
 * All types specific to the Dashboard module.
 * Shared platform types live in @/types.
 */

// -----------------------------------------------
// Overview
// -----------------------------------------------

export interface DashboardDocumentCounts {
  total: number;
  completed: number;
  failed: number;
  processing: number;
  queued: number;
  error?: string;
}

export interface DashboardOverview {
  documents: DashboardDocumentCounts;
  assets: {
    total: number;
    error?: string;
  };
  graph: {
    node_count: number;
    relationship_count: number;
    error?: string;
  };
  embeddings: {
    total_vectors: number;
    note?: string;
  };
}

// -----------------------------------------------
// Documents Widget
// -----------------------------------------------

export interface DashboardDocument {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  processing_stage: string | null;
  upload_time: string;
  document_type: string | null;
  language: string | null;
}

export interface DashboardDocumentsData {
  documents: DashboardDocument[];
  total: number;
}

// -----------------------------------------------
// Assets Widget
// -----------------------------------------------

export interface DashboardAsset {
  entity_id: string;
  name: string;
  entity_type?: string;
  location?: string;
  source_document?: string;
  confidence?: number;
  [key: string]: unknown;
}

export interface DashboardAssetsData {
  assets: DashboardAsset[];
  total: number;
}

// -----------------------------------------------
// System Health Widget
// -----------------------------------------------

export interface ServiceHealth {
  status: 'up' | 'down' | 'healthy' | 'degraded' | string;
  latency_ms: number;
  error?: string;
}

export interface DashboardSystemData {
  overall: 'healthy' | 'degraded';
  services: Record<string, ServiceHealth>;
  checked_at: string;
  duration_ms: number;
}

// -----------------------------------------------
// Knowledge Graph Widget
// -----------------------------------------------

export interface DashboardGraphNode {
  entity_id: string;
  label: string;
  entity_type: string;
  confidence?: number;
  source_document?: string;
  [key: string]: unknown;
}

export interface DashboardGraphData {
  nodes: DashboardGraphNode[];
  total_nodes: number;
  note?: string;
}

// -----------------------------------------------
// Activity Timeline Widget
// -----------------------------------------------

export type ActivityEventType =
  | 'document_uploaded'
  | 'processing_completed'
  | 'graph_updated'
  | 'embeddings_created'
  | 'asset_updated'
  | 'user_search';

export interface ActivityEvent {
  event_type: ActivityEventType | string;
  timestamp: string;
  document_id?: string;
  document_name?: string;
  status?: string;
  detail: string;
}

export interface DashboardActivityData {
  events: ActivityEvent[];
  total: number;
}

// -----------------------------------------------
// Search Analytics Widget
// -----------------------------------------------

export interface DashboardSearchData {
  total_searches: number;
  avg_response_ms: number;
  top_queries: Array<{ query: string; count: number }>;
  note?: string;
}
