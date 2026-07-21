/**
 * Responsive top navbar drawer.
 */

/**
 * @param {ParentNode} [root=document]
 */
export function initNavbar(root = document) {
  const navbar = root.querySelector('[data-navbar]') || document.querySelector('[data-navbar]');
  if (!navbar || navbar.dataset.navbarBound) return;
  navbar.dataset.navbarBound = '1';

  const toggle = navbar.querySelector('[data-navbar-toggle]');
  const drawer = navbar.querySelector('[data-navbar-drawer]');
  if (!toggle || !drawer) return;

  toggle.addEventListener('click', () => {
    const open = drawer.hasAttribute('hidden');
    if (open) {
      drawer.hidden = false;
      drawer.removeAttribute('hidden');
      drawer.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
    } else {
      drawer.hidden = true;
      drawer.setAttribute('hidden', '');
      drawer.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
}

export default { initNavbar };
