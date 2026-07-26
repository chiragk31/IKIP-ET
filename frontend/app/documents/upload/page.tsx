/**
 * Document Upload Page
 *
 * URL: /documents/upload
 *
 * Features:
 * - Drag & drop upload zone
 * - Per-file progress bars
 * - Validation errors displayed inline
 * - Upload history from backend API
 */

import type { Metadata } from 'next';
import { UploadPageClient } from './upload-page-client';

export const metadata: Metadata = {
  title: 'Upload Documents',
  description: 'Upload industrial documents for AI processing, knowledge extraction, and semantic search.',
};

export default function UploadPage() {
  return <UploadPageClient />;
}
