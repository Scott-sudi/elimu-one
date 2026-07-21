import { confirmDialog } from '../core/dialogs.js';

/**
 * Require explicit confirmation before submitting a logout form.
 * @param {ParentNode} [root=document]
 */
export function initLogoutConfirmations(root = document) {
  root.querySelectorAll('[data-logout-confirm]').forEach((form) => {
    if (form.dataset.logoutConfirmBound) return;
    form.dataset.logoutConfirmBound = '1';

    form.addEventListener('submit', async (event) => {
      if (form.dataset.logoutConfirmed === '1') return;

      event.preventDefault();
      const confirmed = await confirmDialog(
        'Voulez-vous vraiment vous déconnecter de votre espace ?',
        {
          title: 'Confirmer la déconnexion',
          confirmLabel: 'Se déconnecter',
          cancelLabel: 'Rester connecté',
          danger: true,
        },
      );

      if (confirmed) {
        form.dataset.logoutConfirmed = '1';
        form.requestSubmit();
      }
    });
  });
}

export default { initLogoutConfirmations };
