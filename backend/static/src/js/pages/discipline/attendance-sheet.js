function computeMention(status) {
  if (status === 'PRESENT') return 'OK';
  return 'ABS';
}

function updateCounters(page) {
  const radios = Array.from(page.querySelectorAll('input[data-sheet-status]:checked'));
  const total = radios.length;
  let present = 0;
  let absent = 0;
  radios.forEach((input) => {
    if (input.value === 'PRESENT') present += 1;
    else absent += 1;
  });
  const totalEl = page.querySelector('[data-sheet-total]');
  const presentEl = page.querySelector('[data-sheet-present]');
  const absentEl = page.querySelector('[data-sheet-absent]');
  const unmarkedEl = page.querySelector('[data-sheet-unmarked]');
  if (totalEl) totalEl.textContent = String(total);
  if (presentEl) presentEl.textContent = String(present);
  if (absentEl) absentEl.textContent = String(absent);
  if (unmarkedEl) unmarkedEl.textContent = '0';
}

function syncMentions(page) {
  const rows = page.querySelectorAll('tbody tr');
  rows.forEach((row) => {
    const selected = row.querySelector('input[data-sheet-status]:checked');
    const mentionCell = row.querySelector('[data-sheet-mention]');
    if (!mentionCell || !selected) return;
    mentionCell.textContent = computeMention(selected.value);
  });
}

function flashRow(row) {
  if (!row) return;
  row.classList.add('is-updated');
  window.setTimeout(() => row.classList.remove('is-updated'), 1200);
}

function applyScannedAttendanceToSheet(page, detail) {
  const matricule = String(detail?.matricule || '')
    .trim()
    .toUpperCase();
  if (!matricule || detail?.duplicate) return;
  const row = page.querySelector(`[data-sheet-row][data-student-matricule="${matricule}"]`);
  if (!row) return;

  // Arrival/exit both keep the student in PRESENT on sheet.
  const presentInput = row.querySelector('input[data-sheet-status][value="PRESENT"]');
  if (presentInput) presentInput.checked = true;

  const mentionCell = row.querySelector('[data-sheet-mention]');
  if (mentionCell) {
    mentionCell.textContent = Number(detail?.lateMinutes || 0) > 0 ? 'RET' : 'OK';
  }

  updateCounters(page);
  flashRow(row);
}

export function initDisciplineAttendanceSheet(root = document) {
  const page = root.querySelector('[data-page="discipline-attendance-sheet"]');
  if (!page || page.dataset.bound === '1') return;
  page.dataset.bound = '1';

  const form = page.querySelector('[data-discipline-sheet-form]');
  if (form) {
    const defaults = new Map();
    form.querySelectorAll('input[data-sheet-status]:checked').forEach((input) => {
      defaults.set(input.name, input.value);
    });

    form.addEventListener('change', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement) || target.type !== 'radio' || !target.dataset.sheetStatus) return;
      syncMentions(page);
      updateCounters(page);
    });

    const markAllBtn = page.querySelector('[data-sheet-mark-all]');
    if (markAllBtn) {
      markAllBtn.addEventListener('click', () => {
        form.querySelectorAll('tbody tr').forEach((row) => {
          const target = row.querySelector('input[data-sheet-status][value="PRESENT"]');
          if (target) target.checked = true;
        });
        syncMentions(page);
        updateCounters(page);
      });
    }

    const resetBtn = page.querySelector('[data-sheet-reset]');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        defaults.forEach((value, name) => {
          const input = form.querySelector(`input[name="${name}"][value="${value}"]`);
          if (input) input.checked = true;
        });
        syncMentions(page);
        updateCounters(page);
      });
    }
  }

  syncMentions(page);
  updateCounters(page);

  if (page.dataset.scanListenerBound !== '1') {
    page.dataset.scanListenerBound = '1';
    document.addEventListener('discipline:attendance-scanned', (event) => {
      applyScannedAttendanceToSheet(page, event?.detail || {});
    });
  }
}

