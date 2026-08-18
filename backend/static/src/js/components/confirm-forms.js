/** Confirm dialogs for forms marked with data-confirm-form. */

import { confirmDialog } from '../core/dialogs.js';

/**
 * Intercept submit on forms that declare data-confirm-form="Message…".
 * Also supports submit buttons with data-confirm (posts parent form).
 * @param {ParentNode} [root=document]
 */
export function initConfirmForms(root = document) {
  root.querySelectorAll('form[data-confirm-form]').forEach((form) => {
    if (form.dataset.confirmBound) return;
    form.dataset.confirmBound = '1';
    form.addEventListener('submit', async (event) => {
      if (form.dataset.confirmAccepted === '1') {
        form.dataset.confirmAccepted = '';
        return;
      }
      event.preventDefault();
      const message = form.getAttribute('data-confirm-form') || 'Confirmer cette opération ?';
      const danger = form.hasAttribute('data-confirm-danger');
      const ok = await confirmDialog(message, {
        confirmLabel: 'Confirmer',
        cancelLabel: 'Annuler',
        danger,
      });
      if (ok) {
        form.dataset.confirmAccepted = '1';
        form.requestSubmit();
      }
    });
  });

  root.querySelectorAll('[data-confirm][data-confirm-submit]').forEach((btn) => {
    if (btn.dataset.confirmBound) return;
    btn.dataset.confirmBound = '1';
    btn.addEventListener('click', async (event) => {
      event.preventDefault();
      const message = btn.getAttribute('data-confirm') || 'Confirmer cette opération ?';
      const ok = await confirmDialog(message, {
        confirmLabel: 'Confirmer',
        cancelLabel: 'Annuler',
        danger: btn.hasAttribute('data-confirm-danger'),
      });
      if (!ok) return;
      const form = btn.closest('form');
      if (form) {
        form.dataset.confirmAccepted = '1';
        form.requestSubmit();
      }
    });
  });
}
