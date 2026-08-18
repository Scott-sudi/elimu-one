import { withCsrfHeaders } from '../../core/csrf.js';
import { toast } from '../../core/notifications.js';
import { createStudentScanner } from '../../components/student-scanner.js';

let activeMode = 'attendance';

function modeText(mode) {
  return mode === 'conduct'
    ? 'Scannez la carte de l’élève ou saisissez son matricule pour consulter sa situation disciplinaire.'
    : 'Scannez la carte de l’élève ou saisissez son matricule pour enregistrer sa présence (entrée).';
}

export function initDisciplineAttendance(root = document) {
  const modal = document.querySelector('[data-discipline-qr-scan-modal]');
  if (!modal || modal.dataset.bound === '1') return;
  modal.dataset.bound = '1';
  const resultEl = modal.querySelector('[data-discipline-scan-result]');
  const hintEl = modal.querySelector('[data-discipline-scan-hint]');

  const scanner = createStudentScanner({
    modal,
    readerId: 'discipline-qr-reader',
    manualInputSelector: '[data-discipline-qr-manual]',
    manualSubmitSelector: '[data-discipline-qr-manual-submit]',
    statusSelector: '[data-discipline-qr-status]',
    onResolve: async ({ raw, setStatus }) => {
      const resolveUrl = modal.getAttribute('data-resolve-url');
      const attendanceUrl = modal.getAttribute('data-attendance-url');
      const identifier = (raw || '').trim();
      if (!identifier) {
        setStatus('Identifiant vide.', 'error');
        return;
      }
      setStatus('Identification de l’élève…');
      const resolveResp = await fetch(resolveUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: withCsrfHeaders({
          Accept: 'application/json',
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({ identifier, mode: activeMode }),
      });
      const resolveBody = await resolveResp.json().catch(() => null);
      if (!resolveResp.ok || !resolveBody?.ok) {
        const msg = resolveBody?.error || 'Identification impossible.';
        setStatus(msg, 'error');
        toast.error(msg);
        return;
      }
      const identity = resolveBody.data || {};
      if (activeMode === 'conduct') {
        const dossierUrl = identity.dossier_url;
        if (!dossierUrl) {
          const msg = 'URL du dossier disciplinaire manquante.';
          setStatus(msg, 'error');
          toast.error(msg);
          return;
        }
        setStatus('Ouverture du dossier disciplinaire…', 'ok');
        toast.success('Élève identifié. Ouverture du dossier…');
        window.location.href = dossierUrl;
        return;
      }
      const attendanceResp = await fetch(attendanceUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: withCsrfHeaders({
          Accept: 'application/json',
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({
          identifier,
          identifier_type: identity.identifier_type,
          class_public_id: modal.getAttribute('data-class-public-id') || '',
          sheet_date: modal.getAttribute('data-sheet-date') || '',
        }),
      });
      const attendanceBody = await attendanceResp.json().catch(() => null);
      if (!attendanceResp.ok || !attendanceBody?.ok) {
        const msg = attendanceBody?.error || 'Pointage échoué.';
        setStatus(msg, 'error');
        toast.error(msg);
        return;
      }
      const data = attendanceBody.data || {};
      if (resultEl) {
        resultEl.textContent =
          `${data.student_name || ''} (${data.matricule || ''}) · ${data.class_name || ''} · ` +
          `${data.operation_label || ''} · ${data.attendance_status || ''}` +
          `${data.late_minutes ? ` · Retard: ${data.late_minutes} min` : ''}`;
      }
      document.dispatchEvent(
        new CustomEvent('discipline:attendance-scanned', {
          detail: {
            matricule: data.matricule || '',
            className: data.class_name || '',
            operation: data.operation || '',
            operationLabel: data.operation_label || '',
            attendanceStatus: data.attendance_status || '',
            lateMinutes: Number(data.late_minutes || 0),
            duplicate: Boolean(data.duplicate),
          },
        }),
      );
      setStatus(attendanceBody.message || 'Pointage enregistré.', 'ok');
      if (data.duplicate) toast.warning(attendanceBody.message || 'Doublon détecté.');
      else toast.success(attendanceBody.message || 'Pointage enregistré.');
    },
  });

  modal.querySelectorAll('[data-scan-mode]').forEach((button) => {
    button.addEventListener('click', () => {
      activeMode = button.getAttribute('data-scan-mode') || 'attendance';
      modal.querySelectorAll('[data-scan-mode]').forEach((btn) => {
        btn.classList.remove('btn--primary');
        btn.classList.add('btn--secondary');
      });
      button.classList.remove('btn--secondary');
      button.classList.add('btn--primary');
      if (hintEl) hintEl.textContent = modeText(activeMode);
      if (resultEl) resultEl.textContent = 'En attente de scan…';
      scanner.setStatus('');
      const input = modal.querySelector('[data-discipline-qr-manual]');
      if (input) input.value = '';
      input?.focus();
    });
  });

  document.querySelectorAll('[data-discipline-open-scanner]').forEach((button) => {
    button.addEventListener('click', () => {
      const mode = button.getAttribute('data-default-mode') || 'attendance';
      activeMode = mode;
      modal.querySelectorAll('[data-scan-mode]').forEach((btn) => {
        const isActive = btn.getAttribute('data-scan-mode') === mode;
        btn.classList.toggle('btn--primary', isActive);
        btn.classList.toggle('btn--secondary', !isActive);
      });
      if (hintEl) hintEl.textContent = modeText(mode);
      if (resultEl) resultEl.textContent = 'En attente de scan…';
      scanner.setStatus('');
      modal.setAttribute('data-class-public-id', button.getAttribute('data-class-public-id') || '');
      modal.setAttribute('data-sheet-date', button.getAttribute('data-sheet-date') || '');
    });
  });

  const page =
    document.querySelector('[data-page="discipline-attendance-daily"]') ||
    document.querySelector('[data-page="discipline-attendance-scan"]');
  if (page) {
    const defaultMode = page.getAttribute('data-default-scanner-mode') || 'attendance';
    activeMode = defaultMode;
    modal.querySelectorAll('[data-scan-mode]').forEach((btn) => {
      const isActive = btn.getAttribute('data-scan-mode') === defaultMode;
      btn.classList.toggle('btn--primary', isActive);
      btn.classList.toggle('btn--secondary', !isActive);
    });
    if (hintEl) hintEl.textContent = modeText(defaultMode);
    if (page.getAttribute('data-auto-open-scanner') === '1') {
      const openBtn = page.querySelector('[data-discipline-open-scanner]');
      window.setTimeout(() => openBtn?.click(), 120);
    }
  }
}

export async function teardownDisciplineAttendance() {
  // Scanner lifecycle handled by shared modal observer.
}

