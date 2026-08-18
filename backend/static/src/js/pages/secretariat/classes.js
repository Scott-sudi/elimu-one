const GUARDIAN_READONLY_CLASS = 'form-input--readonly';

function setReadonlyField(input, value, locked) {
  if (!input) return;
  input.value = value || '';
  input.readOnly = Boolean(locked);
  input.classList.toggle(GUARDIAN_READONLY_CLASS, Boolean(locked));
  input.dataset.locked = locked ? '1' : '0';
  if (locked) input.setAttribute('tabindex', '-1');
  else input.removeAttribute('tabindex');
}

function digitCount(value) {
  return String(value || '').replace(/\D/g, '').length;
}

export function initSecretariatClasses(root = document) {
  const page = root.querySelector('[data-page="secretariat-enrollment"]');
  if (!page || page.dataset.pageBound) return;
  page.dataset.pageBound = '1';

  const lookupUrl = page.dataset.guardianLookupUrl || '';
  const classId = page.dataset.classId || '';
  const phoneInput = page.querySelector('[data-guardian-phone]');
  const nameInput = page.querySelector('[data-guardian-name]');
  const phone2Input = page.querySelector('[data-guardian-phone-2]');
  if (!phoneInput || !lookupUrl) return;

  // Prefer the dedicated template script when present (avoids double-binding).
  if (page.dataset.guardianBound === '1') return;
  page.dataset.guardianBound = '1';

  let lookupTimer = null;
  let hint = phoneInput.parentElement && phoneInput.parentElement.querySelector('.guardian-lookup-hint');
  if (!hint && phoneInput.parentElement) {
    hint = document.createElement('small');
    hint.className = 'guardian-lookup-hint';
    phoneInput.parentElement.appendChild(hint);
  }

  const setHint = (text, kind) => {
    if (!hint) return;
    hint.textContent = text || '';
    hint.classList.toggle('guardian-lookup-hint--known', kind === 'known');
    hint.classList.toggle('guardian-lookup-hint--new', kind === 'new');
    hint.classList.toggle('guardian-lookup-hint--wait', kind === 'wait');
  };

  const lockNameEmpty = () => {
    setReadonlyField(nameInput, '', true);
    if (phone2Input && phone2Input.dataset.locked === '1') {
      setReadonlyField(phone2Input, '', false);
    }
    setHint('Saisissez le téléphone du responsable pour débloquer ou remplir le nom.', 'wait');
  };

  const applyNewGuardian = () => {
    setReadonlyField(nameInput, '', false);
    if (phone2Input && phone2Input.dataset.locked === '1') {
      setReadonlyField(phone2Input, '', false);
    }
    setHint('Nouveau numéro — vous pouvez saisir le nom du responsable.', 'new');
  };

  const applyGuardianMatch = (payload) => {
    setReadonlyField(nameInput, payload.full_name || '', true);
    if (phone2Input && payload.telephone_secondaire) {
      setReadonlyField(phone2Input, payload.telephone_secondaire, true);
    }
    setHint('Responsable déjà connu — nom rempli et verrouillé.', 'known');
  };

  const lookupGuardian = async () => {
    const phone = phoneInput.value.trim();
    if (digitCount(phone) < 9) {
      lockNameEmpty();
      return;
    }
    const params = new URLSearchParams();
    params.set('phone', phone);
    if (classId) params.set('class_id', classId);
    try {
      const response = await fetch(`${lookupUrl}?${params.toString()}`, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      });
      if (!response.ok) {
        applyNewGuardian();
        return;
      }
      const payload = await response.json();
      if (payload.found) {
        applyGuardianMatch(payload);
      } else {
        applyNewGuardian();
      }
    } catch (_error) {
      applyNewGuardian();
    }
  };

  lockNameEmpty();

  phoneInput.addEventListener('input', () => {
    window.clearTimeout(lookupTimer);
    lookupTimer = window.setTimeout(lookupGuardian, 300);
  });
  phoneInput.addEventListener('blur', lookupGuardian);
  phoneInput.addEventListener('change', lookupGuardian);
}
