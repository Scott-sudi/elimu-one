/**
 * Button loading states.
 */

const ATTR = 'data-loading';
const LABEL_ATTR = 'data-loading-label';

/**
 * @param {HTMLButtonElement|HTMLElement|null} button
 * @param {boolean} isLoading
 * @param {{ label?: string }} [options]
 */
export function setButtonLoading(button, isLoading, options = {}) {
  if (!button) return;

  if (isLoading) {
    if (!button.dataset.originalHtml) {
      button.dataset.originalHtml = button.innerHTML;
    }
    button.setAttribute(ATTR, 'true');
    button.setAttribute('aria-busy', 'true');
    if ('disabled' in button) button.disabled = true;

    const label =
      options.label ||
      button.getAttribute(LABEL_ATTR) ||
      'Chargement…';

    button.innerHTML = `<span class="kalunga-btn-spinner" aria-hidden="true"></span><span>${escapeHtml(label)}</span>`;
    ensureSpinnerStyles();
  } else {
    button.removeAttribute(ATTR);
    button.removeAttribute('aria-busy');
    if ('disabled' in button) button.disabled = false;
    if (button.dataset.originalHtml != null) {
      button.innerHTML = button.dataset.originalHtml;
      delete button.dataset.originalHtml;
    }
  }
}

/**
 * Wrap an async action with loading state.
 * @param {HTMLButtonElement|HTMLElement|null} button
 * @param {() => Promise<any>} fn
 * @param {{ label?: string }} [options]
 */
export async function withButtonLoading(button, fn, options = {}) {
  setButtonLoading(button, true, options);
  try {
    return await fn();
  } finally {
    setButtonLoading(button, false);
  }
}

/**
 * @param {string} text
 */
function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function ensureSpinnerStyles() {
  if (document.getElementById('kalunga-loading-styles')) return;
  const style = document.createElement('style');
  style.id = 'kalunga-loading-styles';
  style.textContent = `
    .kalunga-btn-spinner {
      display: inline-block;
      width: 0.85em;
      height: 0.85em;
      margin-right: 0.4em;
      border: 2px solid currentColor;
      border-right-color: transparent;
      border-radius: 50%;
      vertical-align: -0.1em;
      animation: kalunga-spin 160ms linear infinite;
    }
    @keyframes kalunga-spin {
      to { transform: rotate(360deg); }
    }
    button[${ATTR}="true"] {
      opacity: 0.85;
      cursor: wait;
      pointer-events: none;
    }
  `;
  document.head.appendChild(style);
}

export default { setButtonLoading, withButtonLoading };
