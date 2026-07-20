/**
 * Kalunga School — main JS entry.
 * Imports CSS, Alpine, HTMX, Lucide, and all core/components/pages modules.
 */

import '../css/main.css';

import Alpine from 'alpinejs';
import htmx from 'htmx.org';
import { createIcons, icons } from 'lucide';

import { apiFetch, apiGet, apiPost, apiPut, apiPatch, apiDelete } from './core/api.js';
import { getCsrfToken, withCsrfHeaders } from './core/csrf.js';
import { toast, notify } from './core/notifications.js';
import { confirmDialog } from './core/dialogs.js';
import { setButtonLoading, withButtonLoading } from './core/loading.js';

import { initSidebar } from './components/sidebar.js';
import { initModals, openModal, closeModal } from './components/modal.js';
import { initDropdowns } from './components/dropdown.js';
import { initPasswordToggles } from './components/password-toggle.js';
import { initDataTables } from './components/data-table.js';

import { initLogin } from './pages/login.js';
import { initDashboard } from './pages/dashboard.js';
import { initUsers, closeUserModal } from './pages/users.js';
import { initLogins } from './pages/logins.js';
import { initAudit } from './pages/audit.js';
import { initProfile } from './pages/profile.js';

window.htmx = htmx;
window.Alpine = Alpine;

/**
 * Refresh Lucide icons in a root (full document or HTMX swap target).
 * @param {ParentNode} [root=document]
 */
export function refreshIcons(root = document) {
  createIcons({ icons, attrs: { 'stroke-width': 1.75 }, root: root === document ? undefined : root });
}

/**
 * Boot interactive widgets for a given root (initial load or after HTMX).
 * @param {ParentNode} [root=document]
 */
function bootUi(root = document) {
  initSidebar(root);
  initModals(root);
  initDropdowns(root);
  initPasswordToggles(root);
  initDataTables(root);
  refreshIcons(root);
}

function bootPages(root = document) {
  initLogin(root);
  initDashboard(root);
  initUsers(root);
  initLogins(root);
  initAudit(root);
  initProfile(root);
}

function onReady() {
  bootUi(document);
  bootPages(document);
  Alpine.start();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', onReady);
} else {
  onReady();
}

document.body.addEventListener('htmx:afterSwap', (e) => {
  const target = e.target;
  if (target instanceof Element) {
    bootUi(target);
  }
});

document.body.addEventListener('htmx:afterSettle', (e) => {
  const target = e.target;
  if (target instanceof Element) {
    refreshIcons(target);
  }
});

/** Minimal public namespace */
window.Kalunga = {
  api: { fetch: apiFetch, get: apiGet, post: apiPost, put: apiPut, patch: apiPatch, delete: apiDelete },
  csrf: { getToken: getCsrfToken, withHeaders: withCsrfHeaders },
  toast,
  notify,
  confirm: confirmDialog,
  loading: { set: setButtonLoading, with: withButtonLoading },
  modal: { open: openModal, close: closeModal },
  icons: { refresh: refreshIcons },
  users: { closeModal: closeUserModal },
};
