/**
 * Audit log page.
 */

import { initDataTables } from '../components/data-table.js';
import { initDropdowns } from '../components/dropdown.js';

/**
 * @param {ParentNode} [root=document]
 */
export function initAudit(root = document) {
  const page = root.querySelector('[data-page="audit"]') || root.querySelector('[data-audit-page]');
  if (!page || page.dataset.auditBound) return;
  page.dataset.auditBound = '1';

  initDataTables(page);
  initDropdowns(page);

  page.querySelectorAll('[data-audit-detail]').forEach((btn) => {
    if (btn.dataset.auditDetailBound) return;
    btn.dataset.auditDetailBound = '1';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const url = btn.getAttribute('data-audit-detail');
      if (url && window.htmx) {
        window.htmx.ajax('GET', url, {
          target: btn.getAttribute('data-audit-target') || '#audit-detail',
          swap: 'innerHTML',
        });
      }
    });
  });

  document.body.addEventListener('htmx:afterSwap', (e) => {
    if (e.target instanceof Element && (page.contains(e.target) || e.target === page)) {
      initDataTables(e.target);
      initDropdowns(e.target);
    }
  });
}

export default { initAudit };
