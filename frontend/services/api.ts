/**
 * API Service — Axios HTTP Client
 *
 * Central HTTP client for all backend API calls.
 * All API interactions must use this service.
 *
 * Rules:
 * - Never call fetch() or axios directly from components.
 * - Always use service classes built on top of this client.
 * - Authentication headers are added automatically.
 * - All errors are handled and re-thrown with structured messages.
 */

import axios, { AxiosInstance, AxiosProgressEvent, AxiosRequestConfig, AxiosResponse } from 'axios';
import { APIResponse } from '@/types';

// Base URL from environment variable
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

/**
 * Create the configured Axios instance.
 * All service classes use this instance.
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: `${BASE_URL}${API_PREFIX}`,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 seconds
  });

  // Request interceptor — add auth token if available
  client.interceptors.request.use(
    (config) => {
      // Auth token will be added in Phase 10 (Authentication)
      // For now, no auth headers are required
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor — normalize errors
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error) => {
      // Extract structured error message
      const message =
        error.response?.data?.message ||
        error.message ||
        'An unexpected error occurred';

      // Log error details (without stack trace exposure)
      console.error('[API Error]', {
        url: error.config?.url,
        status: error.response?.status,
        message,
      });

      return Promise.reject(new Error(message));
    }
  );

  return client;
};

export const apiClient = createApiClient();

/**
 * Generic GET request helper.
 */
export async function apiGet<T>(
  path: string,
  config?: AxiosRequestConfig
): Promise<APIResponse<T>> {
  const response = await apiClient.get<APIResponse<T>>(path, config);
  return response.data;
}

/**
 * Generic POST request helper.
 */
export async function apiPost<T, B = Record<string, unknown>>(
  path: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<APIResponse<T>> {
  const response = await apiClient.post<APIResponse<T>>(path, body, config);
  return response.data;
}

/**
 * Generic PUT request helper.
 */
export async function apiPut<T, B = Record<string, unknown>>(
  path: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<APIResponse<T>> {
  const response = await apiClient.put<APIResponse<T>>(path, body, config);
  return response.data;
}

/**
 * Generic DELETE request helper.
 */
export async function apiDelete<T>(
  path: string,
  config?: AxiosRequestConfig
): Promise<APIResponse<T>> {
  const response = await apiClient.delete<APIResponse<T>>(path, config);
  return response.data;
}

/**
 * File upload helper with multipart/form-data.
 */
export async function apiUpload<T>(
  path: string,
  formData: FormData,
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
): Promise<APIResponse<T>> {
  const response = await apiClient.post<APIResponse<T>>(path, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  });
  return response.data as APIResponse<T>;
}
