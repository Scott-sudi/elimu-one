function getGlobalFilters() {
  const filters = {};
  document.querySelectorAll('[data-bi-global-filters] select').forEach((select) => {
    if (select instanceof HTMLSelectElement && select.value && select.name !== 'period') {
      filters[select.name] = select.value;
    }
  });
  return filters;
}

export function applyClassFilter(classId) {
  const control = document.querySelector('[data-bi-global-filters] select[name="class_id"]');
  if (!(control instanceof HTMLSelectElement) || !classId) return false;

  control.value = String(classId);
  const next = new URL(window.location.href);
  next.searchParams.set('class_id', String(classId));
  window.history.replaceState({}, '', next);
  document.dispatchEvent(new CustomEvent('bi:filters-change', { detail: getGlobalFilters() }));
  return true;
}

export function bindClassDrilldown(chart, rows, url) {
  if (!chart || !Array.isArray(rows) || !url || chart.dataset.biDrilldownBound === '1') return;
  chart.dataset.biDrilldownBound = '1';
  chart.on?.('plotly_click', (event) => {
    const label = event?.points?.[0]?.label || event?.points?.[0]?.x || event?.points?.[0]?.y;
    const row = rows.find((item) => item.name === label || item.school_class__name === label);
    const classId = row?.class_id || row?.school_class_id || row?.enrollment__school_class_id;
    if (classId && !applyClassFilter(classId)) {
      window.location.assign(`${url}?class_id=${encodeURIComponent(classId)}`);
    }
  });
}