/**
 * Upload Service
 *
 * Handles document file uploads to the backend API.
 * Reports upload progress via callback.
 *
 * Usage:
 *   const result = await UploadService.uploadFile(file, onProgress);
 */

import { apiClient } from '@/services/api';
import { AxiosProgressEvent } from 'axios';
import { UploadResult } from '../types';

export class UploadService {
  /**
   * Upload a file to the backend and track progress.
   *
   * @param file - The File object to upload
   * @param onProgress - Callback receiving 0–100 progress percentage
   * @returns UploadResult with document_id and status
   */
  static async uploadFile(
    file: File,
    onProgress?: (percent: number) => void,
  ): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event: AxiosProgressEvent) => {
        if (event.total && onProgress) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      },
    });

    return response.data.data as UploadResult;
  }
}
