/**
 * Sidebar collapse — expanded 248px / collapsed 72px, persisted in localStorage.
 */

const STORAGE_KEY = 'kalunga.sidebar.collapsed';
const EXPANDED = 248;
const COLLAPSED = 72;
const ANIM_MS = 200;

/**
 * @param {ParentNode} [root=document]
 */
export function initSidebar(root = document) {
  const sidebar = root.querySelector('[data-sidebar]');
  if (!sidebar) return;

  const toggle =
    root.querySelector('[data-sidebar-toggle]') ||
    sidebar.querySelector('[data-sidebar-toggle]');

  applyWidth(sidebar, isCollapsed());

  toggle?.addEventListener('click', (e) => {
    e.preventDefault();
    setCollapsed(!isCollapsed(), sidebar);
  });

  document.addEventListener('kalunga:sidebar-toggle', () => {
    setCollapsed(!isCollapsed(), sidebar);
  });
}

/**
 * @returns {boolean}
 */
export function isCollapsed() {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

/**
 * @param {boolean} collapsed
 * @param {HTMLElement|null} [sidebar]
 */
export function setCollapsed(collapsed, sidebar = null) {
  try {
    localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
  } catch {
    /* ignore quota / private mode */
  }
  const el = sidebar || document.querySelector('[data-sidebar]');
  if (el) applyWidth(el, collapsed);
  document.documentElement.classList.toggle('sidebar-collapsed', collapsed);
  document.dispatchEvent(
    new CustomEvent('kalunga:sidebar-change', { detail: { collapsed } }),
  );
}

/**
 * @param {HTMLElement} sidebar
 * @param {boolean} collapsed
 */
function applyWidth(sidebar, collapsed) {
  const width = collapsed ? COLLAPSED : EXPANDED;
  sidebar.style.transition = `width ${ANIM_MS}ms ease`;
  sidebar.style.width = `${width}px`;
  sidebar.style.minWidth = `${width}px`;
  sidebar.classList.toggle('is-collapsed', collapsed);
  sidebar.setAttribute('data-collapsed', collapsed ? 'true' : 'false');
  sidebar.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  document.documentElement.style.setProperty('--sidebar-width', `${width}px`);
}

export const SIDEBAR_WIDTHS = { EXPANDED, COLLAPSED };

export default { initSidebar, isCollapsed, setCollapsed, SIDEBAR_WIDTHS };
