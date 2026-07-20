/**
 * Password visibility toggle.
 */

/**
 * @param {ParentNode} [root=document]
 */
export function initPasswordToggles(root = document) {
  root.querySelectorAll('[data-password-toggle]').forEach((btn) => {
    if (btn.dataset.passwordBound) return;
    btn.dataset.passwordBound = '1';

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetSel = btn.getAttribute('data-password-toggle');
      const input =
        (targetSel && root.querySelector(targetSel)) ||
        btn.closest('.form-group, .field, label, div')?.querySelector('input[type="password"], input[type="text"]') ||
        btn.previousElementSibling;

      if (!(input instanceof HTMLInputElement)) return;

      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.setAttribute('aria-pressed', show ? 'true' : 'false');
      btn.setAttribute('aria-label', show ? 'Masquer le mot de passe' : 'Afficher le mot de passe');
      btn.classList.toggle('is-visible', show);

      const label = btn.querySelector('[data-password-label]');
      if (label) {
        label.textContent = show ? 'Masquer' : 'Afficher';
      }
    });
  });
}

export default { initPasswordToggles };
