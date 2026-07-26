/**
 * Upload Feature Types
 *
 * TypeScript types specific to the document upload feature.
 */

export type UploadStatus =
  | 'idle'
  | 'validating'
  | 'uploading'
  | 'success'
  | 'error';

export interface UploadedFile {
  /** The file being uploaded */
  file: File;
  /** Current UI upload status */
  status: UploadStatus;
  /** 0–100 progress percentage */
  progress: number;
  /** Error message if status is 'error' */
  error?: string;
  /** Document ID returned by backend after successful upload */
  documentId?: string;
}

export interface UploadResult {
  document_id: string;
  status: string;
  filename: string;
  file_size: number;
  file_type: string;
  upload_time: string;
}

/** Supported file extensions for client-side validation */
export const UPLOAD_ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'text/plain': ['.txt'],
  'text/csv': ['.csv'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/tiff': ['.tiff'],
} as const;

export const MAX_UPLOAD_SIZE_MB = 50;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;
