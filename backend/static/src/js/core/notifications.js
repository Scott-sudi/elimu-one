/**
 * Toast notification system — success / error / warning / info.
 * French UI strings. No gradients. Auto-dismiss + manual close.
 */

const CONTAINER_ID = 'kalunga-toasts';
const DEFAULT_DURATION = 4200;
const ANIM_MS = 180;

const TITLES = {
  success: 'Succès',
  error: 'Erreur',
  warning: 'Attention',
  info: 'Information',
};

/**
 * @returns {HTMLElement}
 */
function ensureContainer() {
  let el = document.getElementById(CONTAINER_ID);
  if (el) return el;

  el = document.createElement('div');
  el.id = CONTAINER_ID;
  el.className = 'kalunga-toast-container';
  el.setAttribute('role', 'region');
  el.setAttribute('aria-live', 'polite');
  el.setAttribute('aria-relevant', 'additions');
  Object.assign(el.style, {
    position: 'fixed',
    top: '1rem',
    right: '1rem',
    zIndex: '9999',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
    maxWidth: 'min(22rem, calc(100vw - 2rem))',
    pointerEvents: 'none',
  });
  document.body.appendChild(el);
  return el;
}

/**
 * @param {'success'|'error'|'warning'|'info'} type
 * @returns {Record<string, string>}
 */
function typeStyles(type) {
  const map = {
    success: { border: 'var(--color-success, #2f9362)', icon: '✓' },
    error: { border: 'var(--color-danger, #d15b5b)', icon: '!' },
    warning: { border: 'var(--color-warning, #d1a13c)', icon: '⚠' },
    info: { border: 'var(--color-information, #4f87c5)', icon: 'i' },
  };
  return map[type] || map.info;
}

/**
 * @param {'success'|'error'|'warning'|'info'} type
 * @param {string} message
 * @param {{ title?: string, duration?: number }} [options]
 * @returns {{ close: () => void }}
 */
export function notify(type, message, options = {}) {
  const container = ensureContainer();
  const duration = options.duration ?? DEFAULT_DURATION;
  const styles = typeStyles(type);
  const title = options.title ?? TITLES[type] ?? TITLES.info;

  const toast = document.createElement('div');
  toast.className = `kalunga-toast kalunga-toast--${type}`;
  toast.setAttribute('role', 'status');
  Object.assign(toast.style, {
    pointerEvents: 'auto',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.65rem',
    padding: '0.75rem 0.85rem',
    borderRadius: '6px',
    border: `1px solid ${styles.border}`,
    background: 'var(--color-surface-elevated, #1a2730)',
    color: 'var(--color-text-primary, #f4f7f5)',
    boxShadow: '0 4px 12px rgba(0,0,0,0.28)',
    opacity: '0',
    transform: 'translateY(-6px)',
    transition: `opacity ${ANIM_MS}ms ease, transform ${ANIM_MS}ms ease`,
  });

  const badge = document.createElement('span');
  badge.setAttribute('aria-hidden', 'true');
  Object.assign(badge.style, {
    flexShrink: '0',
    width: '1.35rem',
    height: '1.35rem',
    borderRadius: '4px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.75rem',
    fontWeight: '700',
    background: 'var(--color-surface, #152028)',
    border: `1px solid ${styles.border}`,
    color: styles.border,
  });
  badge.textContent = styles.icon;

  const body = document.createElement('div');
  body.style.flex = '1';
  body.style.minWidth = '0';

  const titleEl = document.createElement('div');
  titleEl.style.fontWeight = '600';
  titleEl.style.fontSize = '0.85rem';
  titleEl.style.marginBottom = '0.15rem';
  titleEl.textContent = title;

  const msgEl = document.createElement('div');
  msgEl.style.fontSize = '0.8rem';
  msgEl.style.color = 'var(--color-text-secondary, #a2aea8)';
  msgEl.style.lineHeight = '1.35';
  msgEl.textContent = message;

  body.append(titleEl, msgEl);

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.setAttribute('aria-label', 'Fermer');
  closeBtn.textContent = '×';
  Object.assign(closeBtn.style, {
    flexShrink: '0',
    border: 'none',
    background: 'transparent',
    color: 'var(--color-text-secondary, #a2aea8)',
    cursor: 'pointer',
    fontSize: '1.1rem',
    lineHeight: '1',
    padding: '0 0.15rem',
    borderRadius: '4px',
  });

  let timer;
  const close = () => {
    clearTimeout(timer);
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-6px)';
    window.setTimeout(() => toast.remove(), ANIM_MS);
  };

  closeBtn.addEventListener('click', close);
  toast.append(badge, body, closeBtn);
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  if (duration > 0) {
    timer = window.setTimeout(close, duration);
  }

  return { close };
}

export const toast = {
  success: (message, options) => notify('success', message, options),
  error: (message, options) => notify('error', message, options),
  warning: (message, options) => notify('warning', message, options),
  info: (message, options) => notify('info', message, options),
};

export default toast;
