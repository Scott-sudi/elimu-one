/**
 * Confirm dialogs — lightweight, accessible, no gradients.
 */

const ANIM_MS = 160;

/**
 * @param {string} message
 * @param {{
 *   title?: string,
 *   confirmLabel?: string,
 *   cancelLabel?: string,
 *   danger?: boolean,
 * }} [options]
 * @returns {Promise<boolean>}
 */
export function confirmDialog(message, options = {}) {
  const {
    title = 'Confirmation',
    confirmLabel = 'Confirmer',
    cancelLabel = 'Annuler',
    danger = false,
  } = options;

  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'kalunga-dialog-overlay';
    Object.assign(overlay.style, {
      position: 'fixed',
      inset: '0',
      zIndex: '10000',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1rem',
      background: 'var(--color-overlay, rgba(11, 17, 22, 0.72))',
      opacity: '0',
      transition: `opacity ${ANIM_MS}ms ease`,
    });

    const panel = document.createElement('div');
    panel.className = 'kalunga-dialog';
    panel.setAttribute('role', 'alertdialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-labelledby', 'kalunga-dialog-title');
    Object.assign(panel.style, {
      width: 'min(24rem, 100%)',
      borderRadius: '6px',
      border: '1px solid var(--color-border, #2b3940)',
      background: 'var(--color-surface-elevated, #1a2730)',
      color: 'var(--color-text-primary, #f4f7f5)',
      padding: '1.1rem 1.15rem',
      boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
      transform: 'scale(0.98)',
      transition: `transform ${ANIM_MS}ms ease`,
    });

    const titleEl = document.createElement('h2');
    titleEl.id = 'kalunga-dialog-title';
    titleEl.textContent = title;
    Object.assign(titleEl.style, {
      margin: '0 0 0.5rem',
      fontSize: '1rem',
      fontWeight: '600',
    });

    const msgEl = document.createElement('p');
    msgEl.textContent = message;
    Object.assign(msgEl.style, {
      margin: '0 0 1rem',
      fontSize: '0.875rem',
      color: 'var(--color-text-secondary, #a2aea8)',
      lineHeight: '1.45',
    });

    const actions = document.createElement('div');
    Object.assign(actions.style, {
      display: 'flex',
      justifyContent: 'flex-end',
      gap: '0.5rem',
    });

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.textContent = cancelLabel;
    styleBtn(cancelBtn, false);

    const confirmBtn = document.createElement('button');
    confirmBtn.type = 'button';
    confirmBtn.textContent = confirmLabel;
    styleBtn(confirmBtn, true, danger);

    const finish = (value) => {
      overlay.style.opacity = '0';
      panel.style.transform = 'scale(0.98)';
      window.setTimeout(() => {
        overlay.remove();
        document.removeEventListener('keydown', onKey);
        resolve(value);
      }, ANIM_MS);
    };

    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        finish(false);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        finish(true);
      }
    };

    cancelBtn.addEventListener('click', () => finish(false));
    confirmBtn.addEventListener('click', () => finish(true));
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) finish(false);
    });

    actions.append(cancelBtn, confirmBtn);
    panel.append(titleEl, msgEl, actions);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    document.addEventListener('keydown', onKey);

    requestAnimationFrame(() => {
      overlay.style.opacity = '1';
      panel.style.transform = 'scale(1)';
      confirmBtn.focus();
    });
  });
}

/**
 * @param {HTMLButtonElement} btn
 * @param {boolean} primary
 * @param {boolean} [danger=false]
 */
function styleBtn(btn, primary, danger = false) {
  Object.assign(btn.style, {
    borderRadius: '6px',
    padding: '0.45rem 0.85rem',
    fontSize: '0.85rem',
    cursor: 'pointer',
    border: '1px solid var(--color-border, #2b3940)',
    background: primary
      ? danger
        ? 'var(--color-danger, #d15b5b)'
        : 'var(--color-primary, #1f6f4a)'
      : 'var(--color-surface, #152028)',
    color: 'var(--color-text-primary, #f4f7f5)',
    transition: 'background 140ms ease, border-color 140ms ease',
  });
}

export default { confirm: confirmDialog };
