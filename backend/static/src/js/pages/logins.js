/**
 * Login history page.
 */

import { initDataTables } from '../components/data-table.js';

/**
 * @param {ParentNode} [root=document]
 */
export function initLogins(root = document) {
  const page = root.querySelector('[data-page="logins"]') || root.querySelector('[data-logins-page]');
  if (!page || page.dataset.loginsBound) return;
  page.dataset.loginsBound = '1';

  initDataTables(page);

  page.querySelectorAll('[data-logins-filter]').forEach((form) => {
    form.addEventListener('change', () => {
      if (typeof form.requestSubmit === 'function') form.requestSubmit();
      else form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
  });

  document.body.addEventListener('htmx:afterSwap', (e) => {
    if (e.target instanceof Element && page.contains(e.target)) {
      initDataTables(e.target);
    }
  });
}

export default { initLogins };
