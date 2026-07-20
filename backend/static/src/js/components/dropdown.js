/**
 * Dropdown menus — click toggle, outside click, Escape.
 */

const ANIM_MS = 140;

/**
 * @param {ParentNode} [root=document]
 */
export function initDropdowns(root = document) {
  root.querySelectorAll('[data-dropdown]').forEach((dropdown) => {
    if (dropdown.dataset.dropdownBound) return;
    dropdown.dataset.dropdownBound = '1';

    const trigger =
      dropdown.querySelector('[data-dropdown-trigger]') ||
      dropdown.querySelector('button');
    const menu = dropdown.querySelector('[data-dropdown-menu]');
    if (!trigger || !menu) return;

    menu.hidden = true;
    menu.style.transition = `opacity ${ANIM_MS}ms ease, transform ${ANIM_MS}ms ease`;

    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const open = menu.hidden;
      closeAll(root);
      if (open) openMenu(dropdown, trigger, menu);
    });

    menu.querySelectorAll('[data-dropdown-item]').forEach((item) => {
      item.addEventListener('click', () => closeMenu(dropdown, trigger, menu));
    });
  });

  if (!document.documentElement.dataset.dropdownGlobal) {
    document.documentElement.dataset.dropdownGlobal = '1';
    document.addEventListener('click', () => closeAll(document));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeAll(document);
    });
  }
}

/**
 * @param {HTMLElement} dropdown
 * @param {HTMLElement} trigger
 * @param {HTMLElement} menu
 */
function openMenu(dropdown, trigger, menu) {
  menu.hidden = false;
  menu.style.opacity = '0';
  menu.style.transform = 'translateY(-4px)';
  dropdown.classList.add('is-open');
  trigger.setAttribute('aria-expanded', 'true');
  requestAnimationFrame(() => {
    menu.style.opacity = '1';
    menu.style.transform = 'translateY(0)';
  });
}

/**
 * @param {HTMLElement} dropdown
 * @param {HTMLElement} trigger
 * @param {HTMLElement} menu
 */
function closeMenu(dropdown, trigger, menu) {
  menu.style.opacity = '0';
  menu.style.transform = 'translateY(-4px)';
  trigger.setAttribute('aria-expanded', 'false');
  dropdown.classList.remove('is-open');
  window.setTimeout(() => {
    menu.hidden = true;
  }, ANIM_MS);
}

/**
 * @param {ParentNode} root
 */
function closeAll(root) {
  root.querySelectorAll('[data-dropdown].is-open').forEach((dropdown) => {
    const trigger =
      dropdown.querySelector('[data-dropdown-trigger]') ||
      dropdown.querySelector('button');
    const menu = dropdown.querySelector('[data-dropdown-menu]');
    if (trigger && menu) closeMenu(dropdown, trigger, menu);
  });
}

export default { initDropdowns };
