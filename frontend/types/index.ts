/**
 * Shared TypeScript Types
 *
 * All shared type definitions used across the frontend.
 * Feature-specific types live in their respective feature directories.
 */

// -----------------------------------------------
// API Response Types
// -----------------------------------------------

export interface APIResponse<T = Record<string, unknown>> {
  status: 'success' | 'error';
  message: string;
  data?: T;
  errors?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  status: 'success' | 'error';
  message: string;
  data: {
    items: T[];
    pagination: Pagination;
  };
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

// -----------------------------------------------
// Document Types
// -----------------------------------------------

export type DocumentStatus =
  | 'queued'
  | 'uploading'
  | 'uploaded'
  | 'processing'
  | 'parsing'
  | 'ocr_running'
  | 'extracting'
  | 'building_graph'
  | 'generating_embeddings'
  | 'summarizing'
  | 'compliance_check'
  | 'completed'
  | 'failed';

export type DocumentType =
  | 'pdf'
  | 'docx'
  | 'pptx'
  | 'xlsx'
  | 'txt'
  | 'csv'
  | 'png'
  | 'jpg'
  | 'jpeg'
  | 'tiff';

export interface Document {
  id: string;
  userId: string;
  filename: string;
  originalFilename: string;
  storagePath: string;
  fileType: DocumentType;
  fileSize: number;
  uploadTime: string;
  status: DocumentStatus;
  processingStage?: string;
  summary?: string;
  language?: string;
  documentType?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ProcessingJob {
  id: string;
  documentId: string;
  jobType: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt?: string;
  completedAt?: string;
  executionTime?: number;
  errorMessage?: string;
}

// -----------------------------------------------
// Knowledge Graph Types
// -----------------------------------------------

export type EntityType =
  | 'Document'
  | 'Asset'
  | 'Person'
  | 'Organization'
  | 'Location'
  | 'Procedure'
  | 'Event'
  | 'Measurement'
  | 'Risk'
  | 'Failure'
  | 'Regulation'
  | 'Concept';

export interface GraphNode {
  id: string;
  label: string;
  type: EntityType;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  properties: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// -----------------------------------------------
// Asset Types
// -----------------------------------------------

export interface Asset {
  id: string;
  name: string;
  assetType: string;
  subtype?: string;
  manufacturer?: string;
  serialNumber?: string;
  location?: string;
  riskLevel?: 'low' | 'medium' | 'high' | 'critical';
  summary?: string;
  documentCount: number;
  failureCount: number;
  lastMaintenanceDate?: string;
}

// -----------------------------------------------
// Search Types
// -----------------------------------------------

export interface SearchResult {
  chunkId: string;
  documentId: string;
  documentName: string;
  score: number;
  excerpt: string;
  page?: number;
  section?: string;
  assetIds: string[];
}

// -----------------------------------------------
// Chat / AI Copilot Types
// -----------------------------------------------

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  relatedAssets?: string[];
  confidence?: number;
  timestamp: string;
}

export interface Citation {
  documentId: string;
  documentName: string;
  page?: number;
  section?: string;
  excerpt: string;
}

// -----------------------------------------------
// Health Check Types
// -----------------------------------------------

export interface HealthCheckResponse {
  status: 'healthy' | 'degraded';
  services: Record<string, string>;
  durationMs: number;
}

// -----------------------------------------------
// User Types
// -----------------------------------------------

export interface User {
  id: string;
  email: string;
  name?: string;
  role: 'admin' | 'engineer' | 'operator' | 'viewer';
  createdAt: string;
}
