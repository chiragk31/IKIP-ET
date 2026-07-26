/**
 * Frontend Constants
 *
 * Shared constants for the frontend application.
 * Never hardcode these values elsewhere.
 */

// -----------------------------------------------
// API
// -----------------------------------------------

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_V1 = `${API_BASE_URL}/api/v1`;

// -----------------------------------------------
// Document Types
// -----------------------------------------------

export const SUPPORTED_FILE_TYPES = [
  '.pdf',
  '.docx',
  '.pptx',
  '.xlsx',
  '.txt',
  '.csv',
  '.png',
  '.jpg',
  '.jpeg',
  '.tiff',
];

export const SUPPORTED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/plain',
  'text/csv',
  'image/png',
  'image/jpeg',
  'image/tiff',
];

export const MAX_FILE_SIZE_MB = 50;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// -----------------------------------------------
// Pagination
// -----------------------------------------------

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

// -----------------------------------------------
// Search
// -----------------------------------------------

export const DEFAULT_SEARCH_TOP_K = 10;

// -----------------------------------------------
// Document Status Labels
// -----------------------------------------------

export const DOCUMENT_STATUS_LABELS: Record<string, string> = {
  queued: 'Queued',
  uploading: 'Uploading',
  uploaded: 'Uploaded',
  processing: 'Processing',
  parsing: 'Parsing',
  ocr_running: 'Running OCR',
  extracting: 'Extracting Knowledge',
  building_graph: 'Building Graph',
  generating_embeddings: 'Generating Embeddings',
  summarizing: 'Summarizing',
  compliance_check: 'Compliance Check',
  completed: 'Completed',
  failed: 'Failed',
};

// -----------------------------------------------
// Entity Type Colors (for graph visualization)
// -----------------------------------------------

export const ENTITY_TYPE_COLORS: Record<string, string> = {
  Document: '#6366f1',    // Indigo
  Asset: '#f59e0b',       // Amber
  Person: '#10b981',      // Emerald
  Organization: '#3b82f6', // Blue
  Location: '#8b5cf6',    // Purple
  Procedure: '#06b6d4',   // Cyan
  Event: '#ef4444',       // Red
  Measurement: '#f97316', // Orange
  Risk: '#dc2626',        // Dark Red
  Failure: '#991b1b',     // Darker Red
  Regulation: '#64748b',  // Slate
  Concept: '#a78bfa',     // Light Purple
};

// -----------------------------------------------
// Routes
// -----------------------------------------------

export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  DOCUMENTS: '/documents',
  UPLOAD: '/documents/upload',
  GRAPH: '/graph',
  ASSETS: '/assets',
  SEARCH: '/search',
  CHAT: '/chat',
  COMPLIANCE: '/compliance',
  SETTINGS: '/settings',
  LOGIN: '/login',
  REGISTER: '/register',
} as const;
