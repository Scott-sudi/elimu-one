/**
 * BI filter bar — GET form submission + optional API chart refresh.
 */

import { filtersFromForm } from './bi-api.js';

/**
 * Sync empty optional fields out of the query string on submit.
 * @param {HTMLFormElement} form
 */
function cleanSubmit(form) {
  form.addEventListener('submit', () => {
    form.querySelectorAll('input, select').forEach((field) => {
      if (!(field instanceof HTMLInputElement || field instanceof HTMLSelectElement)) return;
      if (!field.name) return;
      if (field.value === '') {
        field.disabled = true;
      }
    });
  });
}

/**
 * @param {HTMLElement} page
 * @param {{ onApply?: (filters: Record<string, string>) => void | Promise<void>, useAjax?: boolean }} [options]
 */
export function initBiFilters(page, options = {}) {
  const form = page.querySelector('[data-bi-filters]');
  if (!(form instanceof HTMLFormElement) || form.dataset.biFiltersBound === '1') {
    return null;
  }
  form.dataset.biFiltersBound = '1';
  cleanSubmit(form);

  const useAjax = options.useAjax === true;

  form.addEventListener('submit', async (event) => {
    if (!useAjax && typeof options.onApply !== 'function') {
      return; // native GET navigation
    }
    event.preventDefault();
    const filters = filtersFromForm(form);
    if (typeof options.onApply === 'function') {
      await options.onApply(filters);
      return;
    }
    const url = new URL(form.action || window.location.href, window.location.origin);
    url.search = '';
    Object.entries(filters).forEach(([k, v]) => url.searchParams.set(k, v));
    window.location.assign(url.toString());
  });

  form.querySelectorAll('[data-bi-filter-reset]').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      const href = btn.getAttribute('href');
      if (href) {
        window.location.assign(href);
        return;
      }
      form.reset();
      form.querySelectorAll('input, select').forEach((field) => {
        if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement) {
          if (field.type !== 'hidden') field.value = '';
        }
      });
      form.requestSubmit();
    });
  });

  return {
    form,
    getFilters: () => filtersFromForm(form),
  };
}

/**
 * Format BiFilters date for <input type="date">.
 * @param {string | { isoformat?: Function } | null | undefined} value
 * @returns {string}
 */
export function dateInputValue(value) {
  if (!value) return '';
  if (typeof value === 'string') {
    return value.slice(0, 10);
  }
  return '';
}

export default { initBiFilters, dateInputValue };
