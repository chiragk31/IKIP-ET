/**
 * Documents List Page
 *
 * URL: /documents
 *
 * Displays all uploaded documents with status, file info, and navigation to upload.
 */

import type { Metadata } from 'next';
import { DocumentsPageClient } from './documents-page-client';

export const metadata: Metadata = {
  title: 'Documents',
  description: 'Browse all uploaded industrial documents, track AI processing status, and manage your knowledge base.',
};

export default function DocumentsPage() {
  return <DocumentsPageClient />;
}
