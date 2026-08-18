/**
 * Finance QR card scanner — opens camera, resolves KAL-CARD-…, redirects to student situation.
 */

import { Html5Qrcode } from 'html5-qrcode';

import { withCsrfHeaders } from '../../core/csrf.js';
import { toast } from '../../core/notifications.js';
import {
  cameraBlockedMessage,
  isCameraSecureContext,
  startHtml5QrWithFallback,
} from '../../core/camera.js';
import { openModal } from '../../components/modal.js';
import { closeModal } from '../../components/modal.js';

let scanner = null;
let resolving = false;
let cameraRunning = false;
let startLock = null;
let wasOpen = false;

function setStatus(modal, message, tone = '') {
  const el = modal.querySelector('[data-finance-qr-status]');
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
    // 2 = SCANNING, 1 = PAUSED — both need stop()
    if (state === 1 || state === 2) {
      await current.stop();
    }
  } catch {
    // ignore
  }
  try {
    await current.clear();
  } catch {
    // ignore
  }
}

async function resolveQr(modal, raw) {
  if (resolving) return;
  const url = modal.getAttribute('data-resolve-url');
  if (!url) {
    setStatus(modal, 'URL de résolution manquante.', 'error');
    return;
  }

  resolving = true;
  setStatus(modal, 'Carte reconnue, ouverture de la situation…', 'ok');

  try {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: withCsrfHeaders({
        Accept: 'application/json',
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({ qr: raw }),
    });
    const body = await response.json().catch(() => null);
    if (!response.ok || !body?.ok) {
      const error = body?.error || 'Impossible de résoudre ce code QR.';
      setStatus(modal, error, 'error');
      toast.error(error);
      resolving = false;
      return;
    }

    const data = body.data || {};
    if (data.warning) {
      toast.warning(data.warning);
    }
    await stopScanner();
    closeModal(modal);
    window.location.href = data.redirect_url;
  } catch {
    const error = 'Erreur réseau lors de la lecture de la carte.';
    setStatus(modal, error, 'error');
    toast.error(error);
    resolving = false;
  }
}

async function startScanner(modal) {
  if (startLock) return startLock;
  if (cameraRunning && scanner) return;

  startLock = (async () => {
    const readerId = 'finance-qr-reader';
    const reader = modal.querySelector('[data-finance-qr-reader]');
    if (!reader) return;

    await stopScanner();
    // Prevent leftover <video> nodes if a previous start raced
    reader.innerHTML = '';
    resolving = false;
    if (!isCameraSecureContext()) {
      setStatus(modal, cameraBlockedMessage(), 'error');
      return;
    }
    setStatus(modal, 'Autorisez la caméra puis présentez le QR de la carte…');

    const instance = new Html5Qrcode(readerId, { verbose: false });
    scanner = instance;
    try {
      await startHtml5QrWithFallback(
        instance,
        {
          fps: 8,
          qrbox: { width: 220, height: 220 },
          aspectRatio: 1.333,
        },
        (decoded) => {
          if (decoded) resolveQr(modal, decoded);
        },
        () => {},
      );
      // Another start may have replaced scanner while we awaited
      if (scanner === instance) {
        cameraRunning = true;
      } else {
        try {
          await instance.stop();
          await instance.clear();
        } catch {
          // ignore
        }
      }
    } catch (err) {
      if (scanner === instance) {
        scanner = null;
        cameraRunning = false;
      }
        console.warn('[finance-qr]', err?.name || err, err?.message || err);
        setStatus(modal, cameraBlockedMessage(err), 'error');
    }
  })();

  try {
    await startLock;
  } finally {
    startLock = null;
  }
}

function resetUi(modal) {
  resolving = false;
  setStatus(modal, '');
  const input = modal.querySelector('[data-finance-qr-manual]');
  if (input) input.value = '';
}

function isModalOpen(modal) {
  return modal.classList.contains('is-open') && !modal.hidden;
}

function bindManual(modal) {
  const input = modal.querySelector('[data-finance-qr-manual]');
  const submit = modal.querySelector('[data-finance-qr-manual-submit]');
  if (submit && submit.dataset.bound !== '1') {
    submit.dataset.bound = '1';
    submit.addEventListener('click', () => {
      const value = input?.value?.trim() || '';
      if (!value) {
        setStatus(modal, 'Saisissez un identifiant QR.', 'error');
        return;
      }
      resolveQr(modal, value);
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

function observeModal(modal) {
  if (modal.dataset.qrObserved === '1') return;
  modal.dataset.qrObserved = '1';
  wasOpen = isModalOpen(modal);

  const observer = new MutationObserver(() => {
    const open = isModalOpen(modal);
    if (open === wasOpen) return;
    wasOpen = open;
    if (open) {
      startScanner(modal);
    } else {
      stopScanner();
      resetUi(modal);
    }
  });
  observer.observe(modal, { attributes: true, attributeFilter: ['class', 'hidden'] });
}

export function initFinanceQrScan(root = document) {
  const modal =
    root.querySelector?.('[data-finance-qr-scan-modal]') ||
    document.querySelector('[data-finance-qr-scan-modal]');
  if (!modal) return;

  bindManual(modal);
  observeModal(modal);
}

/** Allow opening the scanner from console / other modules */
export function openFinanceQrScan() {
  const modal = document.querySelector('[data-finance-qr-scan-modal]');
  if (modal) openModal(modal);
}
