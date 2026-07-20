/**
 * CSRF helpers for Django cookie-based protection.
 */

const CSRF_COOKIE = 'csrftoken';
const CSRF_HEADER = 'X-CSRFToken';

/**
 * @param {string} name
 * @returns {string|null}
 */
export function getCookie(name) {
  if (!document.cookie) return null;
  const parts = document.cookie.split(';');
  for (const part of parts) {
    const [key, ...rest] = part.trim().split('=');
    if (key === name) {
      return decodeURIComponent(rest.join('='));
    }
  }
  return null;
}

/**
 * @returns {string|null}
 */
export function getCsrfToken() {
  return getCookie(CSRF_COOKIE);
}

/**
 * Merge CSRF into Headers / plain object.
 * @param {HeadersInit} [headers={}]
 * @returns {Headers}
 */
export function withCsrfHeaders(headers = {}) {
  const result = new Headers(headers);
  const token = getCsrfToken();
  if (token && !result.has(CSRF_HEADER)) {
    result.set(CSRF_HEADER, token);
  }
  if (!result.has('X-Requested-With')) {
    result.set('X-Requested-With', 'XMLHttpRequest');
  }
  return result;
}

export { CSRF_COOKIE, CSRF_HEADER };
