/**
 * Finance fee form — all classes vs specific target (level / section / option / classes).
 * Also handles class "Créer frais" schedule mode (once / tranches / months).
 * Payment form: fee name then month/tranche period.
 */
export function initFinanceFees(root = document) {
  const page = root.querySelector('[data-page="finance-fees"]');
  if (page) initFeeCreateTargets(page);

  const classCreate = root.querySelector('[data-page="finance-class-fee-create"]');
  if (classCreate) initClassFeeSchedule(classCreate);

  // Modal may exist on class situation page
  const situation = root.querySelector('[data-page="finance-class-situation"]');
  if (situation) {
    const modalCreate = document.querySelector('[data-page="finance-class-fee-create"]');
    if (modalCreate) initClassFeeSchedule(modalCreate);
  }

  const payments = root.querySelector('[data-page="finance-payments"]');
  if (payments) initPaymentFeeGroups(payments);

  const amountChange = root.querySelector('[data-page="finance-amount-change"]');
  if (amountChange) initFeeAmountChange(amountChange);

  const arrears = root.querySelector('[data-page="finance-arrears"]');
  if (arrears) initFinanceListFilters(arrears);

  const paymentsList = root.querySelector('[data-page="finance-payments-list"]');
  if (paymentsList) initFinanceListFilters(paymentsList);

  // Wire column header buttons that open the amount-change modal
  root.querySelectorAll('[data-modal-open="amount-change-modal"][data-fee-id]').forEach((btn) => {
    if (btn.dataset.amountBound === '1') return;
    btn.dataset.amountBound = '1';
    btn.addEventListener('click', () => {
      const modal = document.querySelector('[data-page="finance-amount-change"]');
      if (!modal) return;
      const feeId = btn.getAttribute('data-fee-id') || '';
      const label = btn.getAttribute('data-fee-label') || '';
      const amount = btn.getAttribute('data-fee-amount') || '';
      const idInput = modal.querySelector('#amount-change-fee-id');
      const amountInput = modal.querySelector('#id_new_amount');
      const title = modal.querySelector('[data-amount-change-title]');
      if (idInput) idInput.value = feeId;
      if (amountInput) amountInput.value = amount;
      if (title) title.textContent = label ? `Période : ${label}` : 'Période sélectionnée';
    });
  });
}

function setVisible(node, visible) {
  if (!node) return;
  node.hidden = !visible;
  node.querySelectorAll('select, input, textarea').forEach((el) => {
    el.disabled = !visible;
  });
}

function initFeeCreateTargets(page) {
  const scopeSelect = page.querySelector('[name="target_scope"]');
  const typeSelect = page.querySelector('[name="application_type"]');
  if (!scopeSelect) return;

  const specificBlocks = page.querySelectorAll('[data-fee-specific]');
  const targetGroups = {
    CLASSES_SELECTIONNEES: page.querySelectorAll('[data-fee-target="CLASSES_SELECTIONNEES"]'),
    NIVEAU: page.querySelectorAll('[data-fee-target="NIVEAU"]'),
    SECTION: page.querySelectorAll('[data-fee-target="SECTION"]'),
    OPTION: page.querySelectorAll('[data-fee-target="OPTION"]'),
  };

  function syncTargets() {
    const isSpecific = scopeSelect.value === 'SPECIFIQUE';
    specificBlocks.forEach((node) => setVisible(node, isSpecific));

    if (!isSpecific || !typeSelect) {
      Object.values(targetGroups).forEach((nodes) => {
        nodes.forEach((node) => setVisible(node, false));
      });
      return;
    }

    const selected = typeSelect.value;
    Object.entries(targetGroups).forEach(([key, nodes]) => {
      nodes.forEach((node) => setVisible(node, key === selected));
    });
    setVisible(typeSelect.closest('[data-fee-specific]') || typeSelect.parentElement, true);
  }

  scopeSelect.addEventListener('change', syncTargets);
  if (typeSelect) typeSelect.addEventListener('change', syncTargets);
  syncTargets();
}

function initClassFeeSchedule(root) {
  if (root.dataset.scheduleBound === '1') return;
  root.dataset.scheduleBound = '1';

  const modeSelect = root.querySelector('[name="schedule_mode"]');
  const monthScope = root.querySelector('[name="month_scope"]');
  if (!modeSelect) return;

  const trancheBlocks = root.querySelectorAll('[data-fee-schedule="TRANCHES"]');
  const monthBlocks = root.querySelectorAll('[data-fee-schedule="MOIS"]');
  const monthSelection = root.querySelectorAll('[data-fee-month-selection]');

  function syncSchedule() {
    const mode = modeSelect.value;
    trancheBlocks.forEach((node) => setVisible(node, mode === 'TRANCHES'));
    monthBlocks.forEach((node) => setVisible(node, mode === 'MOIS'));
    const showMonths =
      mode === 'MOIS' && monthScope && monthScope.value === 'SELECTION';
    monthSelection.forEach((node) => setVisible(node, showMonths));
  }

  modeSelect.addEventListener('change', syncSchedule);
  if (monthScope) monthScope.addEventListener('change', syncSchedule);
  syncSchedule();
}

function initFeeAmountChange(root) {
  if (root.dataset.amountChangeBound === '1') return;
  root.dataset.amountChangeBound = '1';

  const scopeInputs = root.querySelectorAll('[data-amount-scope]');
  const classBlock = root.querySelector('[data-amount-class-selection]');
  if (!scopeInputs.length || !classBlock) return;

  function syncScope() {
    const selected = root.querySelector('[data-amount-scope]:checked');
    const show = selected && selected.value === 'CLASSES_SELECTIONNEES';
    setVisible(classBlock, Boolean(show));
  }

  scopeInputs.forEach((input) => input.addEventListener('change', syncScope));
  syncScope();
}

function initFinanceListFilters(page) {
  if (page.dataset.financeFiltersBound === '1') return;
  page.dataset.financeFiltersBound = '1';

  const form = page.querySelector('[data-finance-filters]');
  const dataEl = page.querySelector('#finance-fee-groups-data');
  const levelsEl = page.querySelector('#finance-levels-data');
  const optionSelect = page.querySelector('[data-finance-option]');
  const niveauSelect = page.querySelector('[data-finance-niveau]');
  const fraisSelect = page.querySelector('[data-finance-frais]');
  const periodWrap = page.querySelector('[data-finance-period-wrap]');
  const periodSelect = page.querySelector('[data-finance-periode]');
  const periodLabel = page.querySelector('[data-finance-period-label]');
  const clearWrap = page.querySelector('[data-finance-clear-wrap]');
  if (!dataEl || !fraisSelect || !periodWrap || !periodSelect) return;

  let groups = [];
  let levels = [];
  try {
    groups = JSON.parse(dataEl.textContent || '[]');
  } catch {
    groups = [];
  }
  try {
    levels = JSON.parse(levelsEl?.textContent || '[]');
  } catch {
    levels = [];
  }
  const byKey = Object.fromEntries(groups.map((g) => [g.key, g]));

  function hasActiveFilters() {
    if (!form) return false;
    const data = new FormData(form);
    for (const value of data.values()) {
      if (String(value || '').trim()) return true;
    }
    return false;
  }

  function syncClearButton() {
    if (!clearWrap) return;
    clearWrap.hidden = !hasActiveFilters();
  }

  function syncLevelFilter({ resetIfHidden = false } = {}) {
    if (!niveauSelect) return;
    const optionId = optionSelect?.value || '';
    const previous =
      niveauSelect.value ||
      niveauSelect.getAttribute('data-initial') ||
      new URLSearchParams(window.location.search).get('niveau') ||
      '';

    niveauSelect.innerHTML = '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = 'Tous les niveaux';
    niveauSelect.appendChild(empty);

    const visible = levels.filter((level) => {
      if (!optionId) return true;
      const ids = level.option_ids || [];
      return ids.includes(optionId);
    });

    visible.forEach((level) => {
      const opt = document.createElement('option');
      opt.value = String(level.id);
      opt.textContent = level.label;
      niveauSelect.appendChild(opt);
    });

    if (previous && [...niveauSelect.options].some((o) => o.value === previous)) {
      niveauSelect.value = previous;
    } else if (resetIfHidden) {
      niveauSelect.value = '';
      niveauSelect.removeAttribute('data-initial');
    } else {
      niveauSelect.value = '';
    }
  }

  function syncPeriodFilter() {
    const group = byKey[fraisSelect.value];
    const previous = periodSelect.value;
    periodSelect.innerHTML = '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = 'Toutes';
    periodSelect.appendChild(empty);

    if (!group || group.schedule_mode === 'UNE_FOIS') {
      periodWrap.hidden = true;
      periodSelect.disabled = true;
      periodSelect.value = '';
      syncClearButton();
      return;
    }

    periodWrap.hidden = false;
    periodSelect.disabled = false;
    if (periodLabel) {
      periodLabel.textContent =
        group.schedule_mode === 'MOIS' ? 'Mois' : 'Tranche';
    }
    (group.periods || []).forEach((period) => {
      const opt = document.createElement('option');
      opt.value = String(period.id);
      opt.textContent = period.label;
      periodSelect.appendChild(opt);
    });

    const preferred =
      previous ||
      periodSelect.getAttribute('data-initial') ||
      new URLSearchParams(window.location.search).get('periode') ||
      '';
    if (preferred && [...periodSelect.options].some((o) => o.value === preferred)) {
      periodSelect.value = preferred;
    } else {
      periodSelect.value = '';
    }
    syncClearButton();
  }

  optionSelect?.addEventListener('change', () => {
    syncLevelFilter({ resetIfHidden: true });
    syncClearButton();
  });

  fraisSelect.addEventListener('change', () => {
    periodSelect.value = '';
    periodSelect.removeAttribute('data-initial');
    syncPeriodFilter();
  });

  form?.addEventListener('change', syncClearButton);
  form?.addEventListener('keyup', syncClearButton);
  syncLevelFilter();
  syncPeriodFilter();
  syncClearButton();
}

function initPaymentFeeGroups(page) {
  if (page.dataset.paymentFeesBound === '1') return;
  page.dataset.paymentFeesBound = '1';

  const dataEl = page.querySelector('#payment-fee-groups-data');
  const groupSelect = page.querySelector('[data-payment-fee-group]');
  const periodSelect = page.querySelector('[data-payment-period]');
  const hint = page.querySelector('[data-payment-period-hint]');
  const matriculeInput = page.querySelector('[data-payment-matricule]');
  const studentHint = page.querySelector('[data-payment-student-hint]');
  const emptyFees = page.querySelector('[data-payment-fees-empty]');
  const submitBtn = page.querySelector('[data-payment-submit]');
  const lookupUrl = page.dataset.matriculeLookupUrl || '';
  const stem = page.dataset.matriculeStem || '';
  const classe = page.dataset.classe || '';
  if (!dataEl || !groupSelect || !periodSelect) return;

  let groups = [];
  try {
    groups = JSON.parse(dataEl.textContent || '[]');
  } catch {
    groups = [];
  }
  const initialGroups = groups.slice();
  let byKey = Object.fromEntries(groups.map((g) => [g.key, g]));
  let preferredGroup = groupSelect.value;
  let preferredPeriod = periodSelect.value;
  let lookupTimer = null;
  let lookupSeq = 0;

  function fillEmpty(select, label) {
    select.innerHTML = '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = label || 'Choisir…';
    select.appendChild(empty);
  }

  function setStudentHint(message, tone) {
    if (!studentHint) return;
    if (!message) {
      studentHint.hidden = true;
      studentHint.textContent = '';
      studentHint.classList.remove('is-ok', 'is-error');
      return;
    }
    studentHint.hidden = false;
    studentHint.textContent = message;
    studentHint.classList.toggle('is-ok', tone === 'ok');
    studentHint.classList.toggle('is-error', tone === 'error');
  }

  function applyGroups(nextGroups, { resetSelection = false } = {}) {
    groups = nextGroups || [];
    byKey = Object.fromEntries(groups.map((g) => [g.key, g]));
    dataEl.textContent = JSON.stringify(groups);

    const previousGroup = resetSelection ? '' : preferredGroup || groupSelect.value;
    fillEmpty(groupSelect);
    groups.forEach((group) => {
      const opt = document.createElement('option');
      opt.value = group.key;
      opt.textContent = group.label;
      groupSelect.appendChild(opt);
    });

    const hasFees = groups.length > 0;
    groupSelect.disabled = !hasFees;
    if (submitBtn) submitBtn.disabled = !hasFees;
    if (emptyFees) emptyFees.hidden = hasFees;

    if (previousGroup && byKey[previousGroup]) {
      groupSelect.value = previousGroup;
    } else {
      groupSelect.value = '';
      preferredPeriod = '';
    }
    syncPeriod();
  }

  function syncPeriod() {
    const group = byKey[groupSelect.value];
    fillEmpty(periodSelect);

    if (!group) {
      periodSelect.disabled = true;
      if (hint) hint.textContent = 'Choisissez d’abord un frais.';
      return;
    }

    if (group.schedule_mode === 'UNE_FOIS') {
      periodSelect.disabled = true;
      if (hint) {
        hint.textContent =
          'Ce frais se paie en une seule fois — mois et tranches non applicables.';
      }
      return;
    }

    periodSelect.disabled = false;
    (group.periods || []).forEach((period) => {
      const opt = document.createElement('option');
      opt.value = String(period.id);
      opt.textContent = period.label;
      periodSelect.appendChild(opt);
    });

    if (
      preferredPeriod &&
      [...periodSelect.options].some((o) => o.value === preferredPeriod)
    ) {
      periodSelect.value = preferredPeriod;
    }

    if (hint) {
      hint.textContent =
        group.schedule_mode === 'MOIS'
          ? 'Seuls les mois impayés ou partiellement payés sont proposés.'
          : group.schedule_mode === 'TRANCHES'
            ? 'Seules les tranches impayées ou partiellement payées sont proposées.'
            : 'Ce frais se paie en une seule fois.';
    }
  }

  async function lookupMatricule() {
    if (!lookupUrl || !matriculeInput) return;
    const suffix = (matriculeInput.value || '').trim();
    if (!suffix) {
      setStudentHint('', null);
      if (!classe) {
        preferredGroup = '';
        preferredPeriod = '';
        applyGroups([], { resetSelection: true });
      } else {
        preferredGroup = '';
        preferredPeriod = '';
        applyGroups(initialGroups, { resetSelection: true });
      }
      return;
    }

    const seq = ++lookupSeq;
    const params = new URLSearchParams({ suffix, stem });
    if (classe) params.set('classe', classe);

    try {
      const response = await fetch(`${lookupUrl}?${params.toString()}`, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      });
      const payload = await response.json().catch(() => ({}));
      if (seq !== lookupSeq) return;

      if (!response.ok || !payload.ok) {
        setStudentHint(payload.error || 'Aucun élève trouvé pour ce matricule.', 'error');
        preferredGroup = '';
        preferredPeriod = '';
        applyGroups([], { resetSelection: true });
        return;
      }

      const student = payload.student || {};
      const name = student.name || 'Élève';
      const className = student.class_name || '';
      const matricule = student.matricule || '';
      setStudentHint(
        className
          ? `${name} — Classe : ${className}${matricule ? ` (${matricule})` : ''}`
          : `${name}${matricule ? ` (${matricule})` : ''}`,
        'ok'
      );
      preferredGroup = '';
      preferredPeriod = '';
      applyGroups(payload.fee_groups || [], { resetSelection: true });
    } catch {
      if (seq !== lookupSeq) return;
      setStudentHint('Impossible de vérifier le matricule pour le moment.', 'error');
    }
  }

  function scheduleLookup() {
    clearTimeout(lookupTimer);
    lookupTimer = setTimeout(lookupMatricule, 350);
  }

  groupSelect.addEventListener('change', () => {
    preferredGroup = groupSelect.value;
    preferredPeriod = '';
    syncPeriod();
  });

  if (matriculeInput) {
    matriculeInput.addEventListener('input', scheduleLookup);
    matriculeInput.addEventListener('blur', lookupMatricule);
  }

  // Class context: fees already known; otherwise wait for matricule.
  if (groups.length) {
    applyGroups(groups);
  } else {
    applyGroups([], { resetSelection: true });
  }

  if (matriculeInput && (matriculeInput.value || '').trim()) {
    lookupMatricule();
  }
}
