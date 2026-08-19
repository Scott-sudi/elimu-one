import { Html5Qrcode } from 'html5-qrcode';

import {
  cameraBlockedMessage,
  isCameraSecureContext,
  startHtml5QrWithFallback,
} from '../core/camera.js';

export function createStudentScanner({
  modal,
  readerId,
  manualInputSelector,
  manualSubmitSelector,
  statusSelector,
  onResolve,
}) {
  let scanner = null;
  let cameraRunning = false;
  let resolving = false;
  let startLock = null;
  let wasOpen = false;
  let lastResolvedValue = '';
  let lastResolvedAt = 0;
  const DUPLICATE_COOLDOWN_MS = 2500;

  const manualInput = () => modal.querySelector(manualInputSelector);
  const manualSubmit = () => modal.querySelector(manualSubmitSelector);
  const statusEl = () => modal.querySelector(statusSelector);

  function isOpen() {
    return modal.classList.contains('is-open') && !modal.hidden;
  }

  function setStatus(message, tone = '') {
    const el = statusEl();
    if (!el) return;
    el.textContent = message || '';
    el.classList.toggle('is-error', tone === 'error');
    el.classList.toggle('is-ok', tone === 'ok');
  }

  async function stopScanner() {
    const current = scanner;
    scanner = null;
    cameraRunning = false;
    if (!current) return;
    try {
      const state = current.getState?.();
      if (state === 1 || state === 2) await current.stop();
    } catch {
      // ignore
    }
    try {
      await current.clear();
    } catch {
      // ignore
    }
  }

  async function resolveIdentifier(raw, source = 'manual') {
    if (resolving) return;
    const value = String(raw || '').trim();
    if (!value) return;
    const now = Date.now();
    if (value === lastResolvedValue && now - lastResolvedAt < DUPLICATE_COOLDOWN_MS) {
      return;
    }
    resolving = true;
    lastResolvedValue = value;
    lastResolvedAt = now;
    try {
      await onResolve({
        raw: value,
        source,
        setStatus,
      });
    } finally {
      resolving = false;
      if (manualInput()) manualInput().focus();
    }
  }

  async function startScanner() {
    if (startLock) return startLock;
    if (cameraRunning && scanner) return;
    startLock = (async () => {
      const reader = modal.querySelector(`#${readerId}`);
      if (!reader) return;
      await stopScanner();
      reader.innerHTML = '';
      if (!isCameraSecureContext()) {
        setStatus(cameraBlockedMessage(), 'error');
        return;
      }
      setStatus('Autorisez la caméra puis présentez la carte élève…');
      const instance = new Html5Qrcode(readerId, { verbose: false });
      scanner = instance;
      try {
        await startHtml5QrWithFallback(
          instance,
          { fps: 8, qrbox: { width: 220, height: 220 }, aspectRatio: 1.333 },
          (decoded) => {
            if (decoded) resolveIdentifier(decoded, 'camera');
          },
          () => {},
        );
        if (scanner === instance) cameraRunning = true;
      } catch (err) {
        if (scanner === instance) {
          scanner = null;
          cameraRunning = false;
        }
        console.warn('[student-scanner]', err?.name || err, err?.message || err);
        setStatus(cameraBlockedMessage(err), 'error');
      }
    })();
    try {
      await startLock;
    } finally {
      startLock = null;
    }
  }

  function bindManual() {
    const submit = manualSubmit();
    const input = manualInput();
    if (submit && submit.dataset.bound !== '1') {
      submit.dataset.bound = '1';
      submit.addEventListener('click', () => {
        const value = input?.value?.trim() || '';
        if (!value) {
          setStatus('Saisissez un identifiant (QR ou matricule).', 'error');
          return;
        }
        resolveIdentifier(value, 'manual');
      });
    }
    if (input && input.dataset.bound !== '1') {
      input.dataset.bound = '1';
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          submit?.click();
        }
      });
    }
  }

  function observe() {
    if (modal.dataset.studentScannerObserved === '1') return;
    modal.dataset.studentScannerObserved = '1';
    wasOpen = isOpen();
    const observer = new MutationObserver(() => {
      const open = isOpen();
      if (open === wasOpen) return;
      wasOpen = open;
      if (open) startScanner();
      else stopScanner();
    });
    observer.observe(modal, { attributes: true, attributeFilter: ['class', 'hidden'] });

    // Safety net: modal component emits these events on open/close.
    document.addEventListener('elimu:modal-open', (event) => {
      if (event?.detail?.modal === modal) startScanner();
    });
    document.addEventListener('kalunga:modal-open', (event) => {
      if (event?.detail?.modal === modal) startScanner();
    });
    document.addEventListener('elimu:modal-close', (event) => {
      if (event?.detail?.modal === modal) stopScanner();
    });
    document.addEventListener('kalunga:modal-close', (event) => {
      if (event?.detail?.modal === modal) stopScanner();
    });
  }

  bindManual();
  observe();

  return {
    setStatus,
    stopScanner,
    startScanner,
    resolveIdentifier,
  };
}

