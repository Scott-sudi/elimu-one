/**
 * Users page — HTMX-friendly create/edit modal and actions menu.
 */

import { confirmDialog } from '../core/dialogs.js';
import { toast } from '../core/notifications.js';
import { openModal, closeModal, initModals } from '../components/modal.js';
import { initDropdowns } from '../components/dropdown.js';

/**
 * @param {ParentNode} [root=document]
 */
export function initUsers(root = document) {
  const page = root.querySelector('[data-page="users"]') || root.querySelector('[data-users-page]');
  if (!page) {
    // Still wire global user-modal triggers that may live outside the page marker.
    wireUserModalTriggers(root);
    return;
  }
  if (page.dataset.usersBound) return;
  page.dataset.usersBound = '1';

  initModals(page);
  initDropdowns(page);
  wireUserModalTriggers(page);
  wireUserActions(page);

  document.body.addEventListener('htmx:afterSwap', (e) => {
    const target = e.target;
    if (!(target instanceof Element)) return;
    if (page.contains(target) || target.contains?.(page) || target.matches?.('[data-user-modal], [data-users-table]')) {
      initModals(target);
      initDropdowns(target);
      wireUserModalTriggers(target);
      wireUserActions(target);
    }
  });
}

/**
 * @param {ParentNode} root
 */
function wireUserModalTriggers(root) {
  root.querySelectorAll('[data-user-create]').forEach((btn) => {
    if (btn.dataset.userCreateBound) return;
    btn.dataset.userCreateBound = '1';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const modalId = btn.getAttribute('data-user-create') || 'user-modal';
      resetUserModal(modalId, { mode: 'create' });
      openModal(modalId);
    });
  });

  root.querySelectorAll('[data-user-edit]').forEach((btn) => {
    if (btn.dataset.userEditBound) return;
    btn.dataset.userEditBound = '1';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const userId = btn.getAttribute('data-user-edit');
      const modalId = btn.getAttribute('data-user-modal') || 'user-modal';
      const url = btn.getAttribute('data-user-edit-url') || `/utilisateurs/${userId}/modifier/`;

      resetUserModal(modalId, { mode: 'edit', userId });

      if (window.htmx && btn.hasAttribute('hx-get')) {
        openModal(modalId);
        return;
      }

      if (window.htmx) {
        openModal(modalId);
        window.htmx.ajax('GET', url, {
          target: `#${modalId} [data-user-modal-body]`,
          swap: 'innerHTML',
        });
      } else {
        openModal(modalId);
      }
    });
  });
}

/**
 * @param {ParentNode} root
 */
function wireUserActions(root) {
  root.querySelectorAll('[data-user-delete]').forEach((btn) => {
    if (btn.dataset.userDeleteBound) return;
    btn.dataset.userDeleteBound = '1';
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const name = btn.getAttribute('data-user-name') || 'cet utilisateur';
      const ok = await confirmDialog(
        `Voulez-vous vraiment supprimer ${name} ? Cette action est irréversible.`,
        {
          title: 'Supprimer l’utilisateur',
          confirmLabel: 'Supprimer',
          cancelLabel: 'Annuler',
          danger: true,
        },
      );
      if (!ok) return;

      const url = btn.getAttribute('data-user-delete') || btn.getAttribute('hx-delete');
      if (url && window.htmx) {
        window.htmx.ajax('DELETE', url, {
          target: btn.getAttribute('hx-target') || 'closest tr',
          swap: btn.getAttribute('hx-swap') || 'outerHTML',
        });
      } else {
        toast.info('Suppression en attente de configuration.');
      }
    });
  });

  root.querySelectorAll('[data-user-toggle-active]').forEach((btn) => {
    if (btn.dataset.userToggleBound) return;
    btn.dataset.userToggleBound = '1';
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const activate = btn.getAttribute('data-user-toggle-active') === '1';
      const ok = await confirmDialog(
        activate
          ? 'Activer ce compte utilisateur ?'
          : 'Désactiver ce compte utilisateur ?',
        {
          title: activate ? 'Activer' : 'Désactiver',
          confirmLabel: 'Confirmer',
          cancelLabel: 'Annuler',
        },
      );
      if (!ok) return;
      const url = btn.getAttribute('data-user-toggle-url');
      if (url && window.htmx) {
        window.htmx.ajax('POST', url, { target: 'closest tr', swap: 'outerHTML' });
      }
    });
  });

  root.querySelectorAll('[data-user-status-url]').forEach((btn) => {
    if (btn.dataset.userStatusBound) return;
    btn.dataset.userStatusBound = '1';
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const message = btn.getAttribute('data-confirm') || 'Confirmer cette opération ?';
      const ok = await confirmDialog(message, {
        title: 'Confirmation',
        confirmLabel: 'Confirmer',
        cancelLabel: 'Annuler',
        danger: message.toLowerCase().includes('archiver'),
      });
      if (!ok) return;
      const url = btn.getAttribute('data-user-status-url');
      if (!url) return;
      try {
        const result = await window.Kalunga.api.post(url, {});
        if (result.success) {
          toast.success(result.message || 'Statut mis à jour.');
          const refresh = document.querySelector('[data-users-refresh], #users-filters');
          if (refresh && window.htmx) {
            window.htmx.trigger(refresh, 'submit');
          } else if (window.htmx) {
            window.htmx.ajax('GET', window.location.pathname + window.location.search, {
              target: '#users-table',
              swap: 'outerHTML',
            });
          } else {
            window.location.reload();
          }
        } else {
          toast.error(result.message || 'Opération impossible.');
        }
      } catch (err) {
        toast.error('Le serveur est actuellement inaccessible.');
      }
    });
  });
}

/**
 * @param {string} modalId
 * @param {{ mode: 'create'|'edit', userId?: string|null }} meta
 */
function resetUserModal(modalId, meta) {
  const modal = document.querySelector(`[data-modal="${modalId}"]`) || document.getElementById(modalId);
  if (!modal) return;
  modal.setAttribute('data-user-mode', meta.mode);
  if (meta.userId) modal.setAttribute('data-user-id', meta.userId);
  else modal.removeAttribute('data-user-id');

  const title = modal.querySelector('[data-user-modal-title]');
  if (title) {
    title.textContent = meta.mode === 'create' ? 'Nouvel utilisateur' : 'Modifier l’utilisateur';
  }

  const form = modal.querySelector('form');
  if (form && meta.mode === 'create' && !form.hasAttribute('hx-get')) {
    form.reset();
  }
}

/**
 * Close the user modal after a successful HTMX save.
 * Call from hx-on or listen to htmx:afterRequest.
 */
export function closeUserModal(modalId = 'user-modal') {
  closeModal(modalId);
  toast.success('Utilisateur enregistré.');
}

export default { initUsers, closeUserModal };
