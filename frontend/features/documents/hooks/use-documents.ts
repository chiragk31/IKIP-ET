/**
 * useDocuments Hook
 *
 * Fetches and manages the document list using TanStack Query.
 * Handles pagination and automatic refetching for status updates.
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DocumentService } from '../services/document-service';

export const DOCUMENTS_QUERY_KEY = ['documents'];

export function useDocuments(page = 1, limit = 20) {
  return useQuery({
    queryKey: [...DOCUMENTS_QUERY_KEY, page, limit],
    queryFn: () => DocumentService.listDocuments(page, limit),
    staleTime: 15_000, // Consider fresh for 15 seconds
    refetchInterval: 10_000, // Refetch every 10s (for status updates)
  });
}

export function useDocumentStatus(documentId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['document-status', documentId],
    queryFn: () => DocumentService.getDocumentStatus(documentId!),
    enabled: !!documentId && enabled,
    refetchInterval: (data) => {
      // Stop polling once processing is complete or failed
      const terminal = ['completed', 'failed'];
      if (data && terminal.includes(data.state.data?.status ?? '')) return false;
      return 3_000; // Poll every 3 seconds while in progress
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) => DocumentService.deleteDocument(documentId),
    onSuccess: () => {
      // Invalidate the documents list so it refetches
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
  });
}
