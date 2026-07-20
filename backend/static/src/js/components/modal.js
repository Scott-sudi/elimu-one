/**
 * Modal open/close with Escape and basic focus trap.
 */

const ANIM_MS = 180;
const OPEN_MODALS = new Set();

/**
 * @param {ParentNode} [root=document]
 */
export function initModals(root = document) {
  root.querySelectorAll('[data-modal-open]').forEach((trigger) => {
    if (trigger.dataset.modalBound) return;
    trigger.dataset.modalBound = '1';
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      const id = trigger.getAttribute('data-modal-open');
      if (id) openModal(id);
    });
  });

  root.querySelectorAll('[data-modal-close]').forEach((btn) => {
    if (btn.dataset.modalCloseBound) return;
    btn.dataset.modalCloseBound = '1';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const modal = btn.closest('[data-modal]');
      if (modal) closeModal(modal);
    });
  });

  root.querySelectorAll('[data-modal]').forEach((modal) => {
    if (modal.dataset.modalOverlayBound) return;
    modal.dataset.modalOverlayBound = '1';
    modal.addEventListener('click', (e) => {
      if (e.target === modal || e.target.matches('[data-modal-backdrop]')) {
        closeModal(modal);
      }
    });
  });
}

/**
 * @param {string|HTMLElement} target
 * @returns {HTMLElement|null}
 */
export function openModal(target) {
  const modal = resolveModal(target);
  if (!modal) return null;

  modal.hidden = false;
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  modal.style.opacity = '0';
  modal.style.transition = `opacity ${ANIM_MS}ms ease`;

  const panel = modal.querySelector('[data-modal-panel]') || modal.firstElementChild;
  if (panel) {
    panel.style.transition = `transform ${ANIM_MS}ms ease`;
    panel.style.transform = 'translateY(6px)';
  }

  requestAnimationFrame(() => {
    modal.style.opacity = '1';
    if (panel) panel.style.transform = 'translateY(0)';
  });

  const previouslyFocused = document.activeElement;
  modal._kalungaPrevFocus = previouslyFocused;
  OPEN_MODALS.add(modal);

  const focusable = getFocusable(modal);
  (focusable[0] || modal).focus?.();

  if (!modal._kalungaKeyHandler) {
    modal._kalungaKeyHandler = (e) => onKeyDown(e, modal);
    document.addEventListener('keydown', modal._kalungaKeyHandler);
  }

  document.body.classList.add('modal-open');
  document.dispatchEvent(new CustomEvent('kalunga:modal-open', { detail: { modal } }));
  return modal;
}

/**
 * @param {string|HTMLElement} target
 */
export function closeModal(target) {
  const modal = resolveModal(target);
  if (!modal) return;

  modal.style.opacity = '0';
  const panel = modal.querySelector('[data-modal-panel]') || modal.firstElementChild;
  if (panel) panel.style.transform = 'translateY(6px)';

  window.setTimeout(() => {
    modal.hidden = true;
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
  }, ANIM_MS);

  OPEN_MODALS.delete(modal);
  if (modal._kalungaKeyHandler) {
    document.removeEventListener('keydown', modal._kalungaKeyHandler);
    delete modal._kalungaKeyHandler;
  }

  if (OPEN_MODALS.size === 0) {
    document.body.classList.remove('modal-open');
  }

  const prev = modal._kalungaPrevFocus;
  if (prev && typeof prev.focus === 'function') {
    prev.focus();
  }

  document.dispatchEvent(new CustomEvent('kalunga:modal-close', { detail: { modal } }));
}

/**
 * @param {KeyboardEvent} e
 * @param {HTMLElement} modal
 */
function onKeyDown(e, modal) {
  if (e.key === 'Escape') {
    e.preventDefault();
    closeModal(modal);
    return;
  }
  if (e.key !== 'Tab') return;

  const focusable = getFocusable(modal);
  if (!focusable.length) {
    e.preventDefault();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}

/**
 * @param {HTMLElement} root
 * @returns {HTMLElement[]}
 */
function getFocusable(root) {
  return Array.from(
    root.querySelectorAll(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => !el.hasAttribute('disabled') && el.offsetParent !== null);
}

/**
 * @param {string|HTMLElement} target
 * @returns {HTMLElement|null}
 */
function resolveModal(target) {
  if (!target) return null;
  if (typeof target === 'string') {
    return (
      document.querySelector(`[data-modal="${target}"]`) ||
      document.getElementById(target)
    );
  }
  return target;
}

export default { initModals, openModal, closeModal };
