/**
 * Fetch helpers with CSRF, JSON parsing, and success/error envelope.
 */

import { withCsrfHeaders } from './csrf.js';

/**
 * @typedef {{ ok: true, status: number, data: any, raw: Response }} ApiSuccess
 * @typedef {{ ok: false, status: number, error: string, errors?: any, data?: any, raw?: Response }} ApiError
 * @typedef {ApiSuccess | ApiError} ApiResult
 */

/**
 * @param {Response} response
 * @returns {Promise<any>}
 */
async function parseBody(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
  const text = await response.text();
  return text || null;
}

/**
 * Normalize backend payloads into a consistent envelope.
 * @param {Response} response
 * @param {any} body
 * @returns {ApiResult}
 */
function toEnvelope(response, body) {
  if (response.ok) {
    const data =
      body && typeof body === 'object' && 'data' in body && !('success' in body)
        ? body.data
        : body;
    return { ok: true, status: response.status, data, raw: response };
  }

  let error = 'Une erreur est survenue.';
  let errors;

  if (body && typeof body === 'object') {
    error =
      body.error ||
      body.message ||
      body.detail ||
      (Array.isArray(body.non_field_errors) ? body.non_field_errors[0] : null) ||
      error;
    errors = body.errors || body;
  } else if (typeof body === 'string' && body.trim()) {
    error = body.trim();
  }

  return {
    ok: false,
    status: response.status,
    error: String(error),
    errors,
    data: body,
    raw: response,
  };
}

/**
 * @param {string} url
 * @param {RequestInit} [options={}]
 * @returns {Promise<ApiResult>}
 */
export async function apiFetch(url, options = {}) {
  const headers = withCsrfHeaders(options.headers || {});

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !(options.body instanceof URLSearchParams) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options,
      headers,
    });
    const body = await parseBody(response);
    return toEnvelope(response, body);
  } catch (err) {
    return {
      ok: false,
      status: 0,
      error: err instanceof Error ? err.message : 'Impossible de contacter le serveur.',
    };
  }
}

/**
 * @param {string} url
 * @param {Record<string, any>|FormData|URLSearchParams} [data]
 * @param {RequestInit} [options={}]
 */
export function apiGet(url, options = {}) {
  return apiFetch(url, { ...options, method: 'GET' });
}

/**
 * @param {string} url
 * @param {Record<string, any>|FormData|URLSearchParams} [data]
 * @param {RequestInit} [options={}]
 */
export function apiPost(url, data, options = {}) {
  return apiFetch(url, {
    ...options,
    method: 'POST',
    body: serializeBody(data, options.headers),
  });
}

/**
 * @param {string} url
 * @param {Record<string, any>|FormData|URLSearchParams} [data]
 * @param {RequestInit} [options={}]
 */
export function apiPut(url, data, options = {}) {
  return apiFetch(url, {
    ...options,
    method: 'PUT',
    body: serializeBody(data, options.headers),
  });
}

/**
 * @param {string} url
 * @param {Record<string, any>|FormData|URLSearchParams} [data]
 * @param {RequestInit} [options={}]
 */
export function apiPatch(url, data, options = {}) {
  return apiFetch(url, {
    ...options,
    method: 'PATCH',
    body: serializeBody(data, options.headers),
  });
}

/**
 * @param {string} url
 * @param {RequestInit} [options={}]
 */
export function apiDelete(url, options = {}) {
  return apiFetch(url, { ...options, method: 'DELETE' });
}

/**
 * @param {Record<string, any>|FormData|URLSearchParams|undefined} data
 * @param {HeadersInit} [headers]
 */
function serializeBody(data, headers) {
  if (data == null) return undefined;
  if (data instanceof FormData || data instanceof URLSearchParams) return data;
  const hdrs = new Headers(headers || {});
  if (hdrs.get('Content-Type') === 'application/x-www-form-urlencoded') {
    return new URLSearchParams(data);
  }
  return JSON.stringify(data);
}
