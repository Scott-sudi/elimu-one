/**
 * Matricule → class autofill for Discipline create modals
 * (incidents, conduite, sorties).
 */

function bindMatriculeAutofill(form, lookupUrl) {
  const matriculeInput = form.querySelector('[data-matricule-input]');
  const classInput = form.querySelector('[data-class-input]');
  const hintEl = form.querySelector('[data-student-hint]');
  if (!matriculeInput || !classInput || !lookupUrl) return;

  let timer = null;
  let seq = 0;
  const defaultHint = hintEl ? hintEl.textContent : '';

  function setHint(text, ok) {
    if (!hintEl) return;
    hintEl.textContent = text || defaultHint;
    if (ok === false) {
      hintEl.style.color = 'var(--color-danger, #b42318)';
    } else {
      hintEl.style.color = '';
    }
  }

  function clearClass() {
    classInput.value = '';
  }

  async function lookup() {
    const matricule = (matriculeInput.value || '').trim();
    if (!matricule) {
      clearClass();
      setHint(defaultHint, null);
      return;
    }
    const requestId = ++seq;
    try {
      const response = await fetch(
        `${lookupUrl}?${new URLSearchParams({ matricule }).toString()}`,
        { headers: { Accept: 'application/json' }, credentials: 'same-origin' },
      );
      const payload = await response.json().catch(() => ({}));
      if (requestId !== seq) return;
      if (!response.ok || !payload.ok) {
        clearClass();
        setHint(payload.error || 'Élève introuvable pour ce matricule.', false);
        return;
      }
      const data = payload.data || {};
      classInput.value = data.class_name || '';
      const name = data.full_name || '';
      setHint(name ? `${name} · ${data.matricule || matricule}` : defaultHint, true);
    } catch {
      if (requestId !== seq) return;
      clearClass();
      setHint('Impossible de vérifier le matricule.', false);
    }
  }

  function scheduleLookup() {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(lookup, 350);
  }

  matriculeInput.addEventListener('input', scheduleLookup);
  matriculeInput.addEventListener('blur', lookup);

  if ((matriculeInput.value || '').trim()) {
    lookup();
  }
}

export function initDisciplineIncidents(root = document) {
  const pages = root.querySelectorAll(
    '[data-page="discipline-incidents-list"], [data-page="discipline-exits-list"], [data-page="discipline-summons-list"]',
  );
  pages.forEach((page) => {
    const lookupUrl = page.dataset.incidentLookupUrl || '';
    page.querySelectorAll('[data-matricule-autofill-form]').forEach((form) => {
      bindMatriculeAutofill(form, lookupUrl);
    });
  });

  // Also bind forms that may live in {% block modals %} outside data-page
  document.querySelectorAll('[data-matricule-autofill-form]').forEach((form) => {
    if (form.dataset.matriculeBound === '1') return;
    const page =
      form.closest('[data-incident-lookup-url]') ||
      document.querySelector(
        '[data-page="discipline-incidents-list"], [data-page="discipline-exits-list"], [data-page="discipline-summons-list"]',
      );
    const lookupUrl = page?.dataset?.incidentLookupUrl || '';
    if (!lookupUrl) return;
    form.dataset.matriculeBound = '1';
    bindMatriculeAutofill(form, lookupUrl);
  });
}
