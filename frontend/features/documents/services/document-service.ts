/**
 * Document Service
 *
 * Handles all document API calls: list, detail, status polling, delete.
 */

import { apiClient } from '@/services/api';

export interface DocumentListItem {
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

export interface DocumentListResult {
  documents: DocumentListItem[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface DocumentDetail {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  status: string;
  processing_stage: string | null;
  summary: string | null;
  document_type: string | null;
  language: string | null;
  upload_time: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentStatus {
  document_id: string;
  status: string;
  processing_stage: string | null;
  updated_at: string;
}

export class DocumentService {
  /**
   * List all documents with pagination.
   */
  static async listDocuments(page = 1, limit = 20): Promise<DocumentListResult> {
    const response = await apiClient.get('/documents/', {
      params: { page, limit },
    });
    return response.data.data as DocumentListResult;
  }

  /**
   * Get full details for a single document.
   */
  static async getDocument(documentId: string): Promise<DocumentDetail> {
    const response = await apiClient.get(`/documents/${documentId}`);
    return response.data.data as DocumentDetail;
  }

  /**
   * Poll the processing status of a document.
   * Frontend calls this every 3-5s to track AI pipeline progress.
   */
  static async getDocumentStatus(documentId: string): Promise<DocumentStatus> {
    const response = await apiClient.get(`/documents/${documentId}/status`);
    return response.data.data as DocumentStatus;
  }

  /**
   * Delete a document and its file from storage.
   */
  static async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/documents/${documentId}`);
  }
}
