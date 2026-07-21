/**
 * Users page — create/edit modal and status actions.
 */

import { confirmDialog } from '../core/dialogs.js';
import { toast } from '../core/notifications.js';
import { openModal, closeModal, initModals } from '../components/modal.js';
import { initDropdowns } from '../components/dropdown.js';
import { initPasswordToggles } from '../components/password-toggle.js';
import { setButtonLoading } from '../core/loading.js';
import { apiPost } from '../core/api.js';

/**
 * @param {ParentNode} [root=document]
 */
export function initUsers(root = document) {
  const page = root.querySelector('[data-page="users"]') || root.querySelector('[data-users-page]');
  if (!page) return;
  const scope = page || root;

  wireUserModalTriggers(scope);
  wireUserActions(scope);
  // Le formulaire de création est dans #modal-root, hors de la page
  wireUserForms(document);
  initModals(document);
  initDropdowns(scope);

  if (!document.body.dataset.usersHtmxBound) {
    document.body.dataset.usersHtmxBound = '1';
    document.body.addEventListener('htmx:afterSwap', (e) => {
      const target = e.target;
      if (!(target instanceof Element)) return;
      initDropdowns(target);
      wireUserActions(target);
      wireUserForms(document);
      initPasswordToggles(target);
      if (window.Kalunga?.icons?.refresh) window.Kalunga.icons.refresh(target);
    });
  }
}

function wireUserModalTriggers(root) {
  root.querySelectorAll('[data-user-create]').forEach((btn) => {
    if (btn.dataset.userCreateBound) return;
    btn.dataset.userCreateBound = '1';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const modalId = btn.getAttribute('data-user-create') || 'user-modal';
      const modal = openModal(modalId);
      if (!modal) {
        toast.error('Impossible d’ouvrir le formulaire.');
        return;
      }
      const title = modal.querySelector('[data-user-modal-title]');
      if (title) title.textContent = 'Nouvel utilisateur';
      const form = modal.querySelector('form[data-user-form]');
      if (form) {
        form.reset();
        form.dataset.mode = 'create';
      }
      initPasswordToggles(modal);
    });
  });

  root.querySelectorAll('[data-user-edit]').forEach((btn) => {
    if (btn.dataset.userEditBound) return;
    btn.dataset.userEditBound = '1';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const modalId = btn.getAttribute('data-user-modal') || 'user-modal';
      const url = btn.getAttribute('data-user-edit-url');
      openModal(modalId);
      if (url && window.htmx) {
        window.htmx.ajax('GET', url, {
          target: `#${modalId} [data-user-modal-body]`,
          swap: 'innerHTML',
        });
      }
    });
  });
}

function wireUserForms(root) {
  root.querySelectorAll('form[data-user-form]').forEach((form) => {
    if (form.dataset.userFormBound) return;
    form.dataset.userFormBound = '1';
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = form.querySelector('[type="submit"], [data-user-submit]');
      const action = form.getAttribute('action');
      if (!action) {
        toast.error('Action du formulaire manquante.');
        return;
      }

      const formData = new FormData(form);
      const payload = Object.fromEntries(formData.entries());
      payload.is_active = formData.get('is_active') ? true : false;
      payload.must_change_password = formData.get('must_change_password') ? true : false;

      setButtonLoading(submitBtn, true);
      try {
        const result = await apiPost(action, payload, {
          headers: { Accept: 'application/json' },
        });
        const body = result.data || {};
        const success = result.ok && body.success !== false;
        if (success) {
          toast.success(body.message || 'Opération réussie.');
          closeModal(form.closest('[data-modal]') || 'user-modal');
          refreshUsersTable();
        } else {
          toast.error(body.message || result.error || 'Formulaire invalide.');
        }
      } catch (err) {
        console.error(err);
        toast.error('Le serveur est actuellement inaccessible.');
      } finally {
        setButtonLoading(submitBtn, false);
      }
    });
  });
}

function refreshUsersTable() {
  if (window.htmx) {
    window.htmx.ajax('GET', window.location.pathname + window.location.search, {
      target: '#users-table',
      swap: 'outerHTML',
    });
  } else {
    window.location.reload();
  }
}

function wireUserActions(root) {
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
      try {
        const result = await apiPost(url, {});
        const body = result.data || {};
        if (result.ok && body.success !== false) {
          toast.success(body.message || 'Statut mis à jour.');
          refreshUsersTable();
        } else {
          toast.error(body.message || result.error || 'Opération impossible.');
        }
      } catch (err) {
        toast.error('Le serveur est actuellement inaccessible.');
      }
    });
  });
}

export function closeUserModal(modalId = 'user-modal') {
  closeModal(modalId);
}

export default { initUsers, closeUserModal };
