export function initFilterManager(root = document) {
  const controls = root.querySelector('[data-bi-global-filters]');
  if (!(controls instanceof HTMLElement) || controls.dataset.biBound === '1') return null;
  controls.dataset.biBound = '1';
  const url = new URL(window.location.href);
  controls.querySelectorAll('select').forEach((select) => {
    if (!(select instanceof HTMLSelectElement)) return;
    select.value = url.searchParams.get(select.name) || '';
    select.addEventListener('change', () => {
      const filters = getFilters(controls);
      const next = new URL(window.location.href);
      ['class_id', 'section', 'option'].forEach((key) => next.searchParams.delete(key));
      Object.entries(filters).forEach(([key, value]) => { if (value) next.searchParams.set(key, value); });
      window.history.replaceState({}, '', next);
      document.dispatchEvent(new CustomEvent('bi:filters-change', { detail: filters }));
    });
  });
  return { getFilters: () => getFilters(controls) };
}

export function getFilters(root = document) {
  const filters = {};
  root.querySelectorAll('[data-bi-global-filters] select').forEach((select) => {
    if (select instanceof HTMLSelectElement && select.value && select.name !== 'period') filters[select.name] = select.value;
  });
  return filters;
}