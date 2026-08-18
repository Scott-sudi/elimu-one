/**
 * Auto-refresh list pages when filter controls change.
 * Full-page GET submit for classic toolbars (not HTMX forms).
 */

const FILTER_FORM_SELECTOR = [
  'form[data-auto-filter]',
  'form.secretariat-toolbar--filters',
  'form.finance-filters',
].join(', ');

export function initAutoFilterForms(root = document) {
  const scope = root instanceof Element || root instanceof Document ? root : document;

  scope.querySelectorAll(FILTER_FORM_SELECTOR).forEach((form) => {
    if (!(form instanceof HTMLFormElement)) return;
    if ((form.method || 'get').toLowerCase() !== 'get') return;
    // Already live-filtered via HTMX — do not double-submit.
    if (form.hasAttribute('hx-get') || form.hasAttribute('hx-post') || form.hasAttribute('data-finance-filters')) {
      return;
    }
    if (form.dataset.autoFilterBound === '1') return;
    form.dataset.autoFilterBound = '1';
    form.setAttribute('data-auto-filter', '1');

    let timer = null;

    function submitNow() {
      if (typeof form.requestSubmit === 'function') {
        try {
          form.requestSubmit();
          return;
        } catch {
          // fall through
        }
      }
      form.submit();
    }

    form.addEventListener('change', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (!form.contains(target)) return;
      if (target.matches('select, input[type="date"], input[type="month"], input[type="checkbox"], input[type="radio"]')) {
        submitNow();
      }
    });

    form.querySelectorAll('input[type="search"], input[name="q"]').forEach((input) => {
      input.addEventListener('input', () => {
        if (timer) window.clearTimeout(timer);
        timer = window.setTimeout(submitNow, 350);
      });
    });
  });
}
