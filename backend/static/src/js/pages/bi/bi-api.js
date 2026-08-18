/**
 * BI API client with AbortController support.
 */

import { apiFetch } from '../../core/api.js';

const API_BASE = '/api/v1/bi';

/** @type {Map<string, AbortController>} */
const inflight = new Map();

/**
 * @param {Record<string, string | number | boolean | null | undefined>} [params]
 * @returns {string}
 */
export function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value == null || value === '') return;
    search.set(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

/**
 * Read current BI filter values from a form or the URL.
 * @param {HTMLFormElement | null} [form]
 * @returns {Record<string, string>}
 */
export function filtersFromForm(form) {
  /** @type {Record<string, string>} */
  const out = {};
  if (form instanceof HTMLFormElement) {
    const data = new FormData(form);
    data.forEach((value, key) => {
      if (typeof value === 'string' && value.trim() !== '') {
        out[key] = value.trim();
      }
    });
    return out;
  }
  const params = new URLSearchParams(window.location.search);
  params.forEach((value, key) => {
    if (value.trim() !== '') out[key] = value.trim();
  });
  return out;
}

/**
 * Abort any in-flight request for the same key, then fetch.
 * @param {string} path - path under /api/v1/bi/
 * @param {Record<string, string | number | boolean | null | undefined>} [params]
 * @param {{ key?: string, signal?: AbortSignal }} [options]
 * @returns {Promise<import('../../core/api.js').ApiResult>}
 */
export async function biFetch(path, params = {}, options = {}) {
  const key = options.key || path;
  const previous = inflight.get(key);
  if (previous) previous.abort();

  const controller = new AbortController();
  inflight.set(key, controller);

  const external = options.signal;
  if (external) {
    if (external.aborted) controller.abort();
    else {
      external.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  const url = `${API_BASE}/${path.replace(/^\//, '')}${buildQuery(params)}`;

  try {
    const result = await apiFetch(url, { method: 'GET', signal: controller.signal });
    if (controller.signal.aborted) {
      return { ok: false, status: 0, error: 'cancelled' };
    }
    return result;
  } finally {
    if (inflight.get(key) === controller) {
      inflight.delete(key);
    }
  }
}

/**
 * @param {string} domain - enrollments | financial | attendance | discipline | classes | comparisons
 * @param {'summary' | 'trends' | 'classes'} section
 * @param {Record<string, string>} [filters]
 * @param {{ key?: string, signal?: AbortSignal }} [options]
 */
export function biDomainFetch(domain, section, filters = {}, options = {}) {
  return biFetch(`${domain}/${section}/`, filters, {
    key: options.key || `bi:${domain}:${section}`,
    signal: options.signal,
  });
}

/**
 * @param {Record<string, string>} [filters]
 * @param {{ key?: string, signal?: AbortSignal }} [options]
 */
export function biOverviewFetch(filters = {}, options = {}) {
  return biFetch('overview/', filters, {
    key: options.key || 'bi:overview',
    signal: options.signal,
  });
}

export default {
  buildQuery,
  filtersFromForm,
  biFetch,
  biDomainFetch,
  biOverviewFetch,
};
