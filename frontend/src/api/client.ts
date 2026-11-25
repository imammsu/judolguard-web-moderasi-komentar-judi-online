import type { ApiResponse } from '../types/api';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/**
 * Klien fetch bertipe. Cookie sesi HttpOnly ikut terkirim (credentials: 'include');
 * token OAuth tidak pernah disimpan di browser (PRD 14.1).
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { headers, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(path, {
      credentials: 'include',
      ...rest,
      headers: {
        Accept: 'application/json',
        ...(rest.body ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
    });
  } catch {
    throw new ApiError(0, 'network_error', 'Tidak dapat terhubung ke server backend.');
  }

  let body: ApiResponse<T> | null = null;
  try {
    body = (await res.json()) as ApiResponse<T>;
  } catch {
    body = null;
  }

  if (!body) {
    throw new ApiError(res.status, 'invalid_response', `Respons server tidak valid (HTTP ${res.status}).`);
  }
  if (!body.success) {
    throw new ApiError(res.status, body.error.code, body.error.message);
  }
  if (!res.ok) {
    throw new ApiError(res.status, 'http_error', `HTTP ${res.status}`);
  }
  return body.data;
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, data?: unknown) =>
    apiFetch<T>(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: 'DELETE' }),
};
