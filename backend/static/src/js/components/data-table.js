/**
 * Lightweight data-table helpers (sort hint, row selection, empty state).
 */

/**
 * @param {ParentNode} [root=document]
 */
export function initDataTables(root = document) {
  root.querySelectorAll('[data-table]').forEach((table) => {
    if (table.dataset.tableBound) return;
    table.dataset.tableBound = '1';

    initSortableHeaders(table);
    initRowSelection(table);
    updateEmptyState(table);
  });
}

/**
 * @param {HTMLElement} table
 */
function initSortableHeaders(table) {
  table.querySelectorAll('[data-sort-key]').forEach((th) => {
    th.style.cursor = 'pointer';
    th.setAttribute('role', 'columnheader');
    th.addEventListener('click', () => {
      const key = th.getAttribute('data-sort-key');
      if (!key) return;
      const current = th.getAttribute('data-sort-dir') || 'none';
      const next = current === 'asc' ? 'desc' : 'asc';

      table.querySelectorAll('[data-sort-key]').forEach((h) => {
        h.removeAttribute('data-sort-dir');
        h.setAttribute('aria-sort', 'none');
      });
      th.setAttribute('data-sort-dir', next);
      th.setAttribute('aria-sort', next === 'asc' ? 'ascending' : 'descending');

      sortRows(table, key, next);
    });
  });
}

/**
 * @param {HTMLElement} table
 * @param {string} key
 * @param {'asc'|'desc'} dir
 */
function sortRows(table, key, dir) {
  const tbody = table.querySelector('tbody');
  if (!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr[data-row]'));
  rows.sort((a, b) => {
    const av = (a.getAttribute(`data-${key}`) || a.querySelector(`[data-col="${key}"]`)?.textContent || '').trim();
    const bv = (b.getAttribute(`data-${key}`) || b.querySelector(`[data-col="${key}"]`)?.textContent || '').trim();
    const an = Number(av);
    const bn = Number(bv);
    let cmp;
    if (!Number.isNaN(an) && !Number.isNaN(bn) && av !== '' && bv !== '') {
      cmp = an - bn;
    } else {
      cmp = av.localeCompare(bv, 'fr', { sensitivity: 'base' });
    }
    return dir === 'asc' ? cmp : -cmp;
  });
  rows.forEach((row) => tbody.appendChild(row));
}

/**
 * @param {HTMLElement} table
 */
function initRowSelection(table) {
  const master = table.querySelector('[data-select-all]');
  const getBoxes = () =>
    Array.from(table.querySelectorAll('tbody [data-select-row]'));

  master?.addEventListener('change', () => {
    getBoxes().forEach((box) => {
      box.checked = master.checked;
      box.closest('tr')?.classList.toggle('is-selected', master.checked);
    });
    emitSelection(table);
  });

  table.addEventListener('change', (e) => {
    const target = e.target;
    if (!(target instanceof HTMLInputElement)) return;
    if (!target.matches('[data-select-row]')) return;
    target.closest('tr')?.classList.toggle('is-selected', target.checked);
    if (master) {
      const boxes = getBoxes();
      master.checked = boxes.length > 0 && boxes.every((b) => b.checked);
      master.indeterminate = boxes.some((b) => b.checked) && !master.checked;
    }
    emitSelection(table);
  });
}

/**
 * @param {HTMLElement} table
 */
function emitSelection(table) {
  const ids = Array.from(table.querySelectorAll('tbody [data-select-row]:checked'))
    .map((el) => el.value || el.closest('tr')?.getAttribute('data-id'))
    .filter(Boolean);
  table.dispatchEvent(
    new CustomEvent('kalunga:table-selection', {
      bubbles: true,
      detail: { ids, count: ids.length },
    }),
  );
}

/**
 * @param {HTMLElement} table
 */
export function updateEmptyState(table) {
  const tbody = table.querySelector('tbody');
  const empty = table.parentElement?.querySelector('[data-table-empty]');
  if (!tbody || !empty) return;
  const hasRows = tbody.querySelectorAll('tr[data-row]').length > 0;
  empty.hidden = hasRows;
  tbody.hidden = !hasRows;
}

/**
 * @param {HTMLElement} table
 * @returns {string[]}
 */
export function getSelectedIds(table) {
  return Array.from(table.querySelectorAll('tbody [data-select-row]:checked'))
    .map((el) => el.value || el.closest('tr')?.getAttribute('data-id'))
    .filter(Boolean);
}

export default { initDataTables, updateEmptyState, getSelectedIds };
