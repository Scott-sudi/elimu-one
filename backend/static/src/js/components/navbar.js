/**
 * Sliding side navigation panel (overlay — does not push page content).
 */

/**
 * @param {ParentNode} [root=document]
 */
export function initNavbar(root = document) {
  const navbar = root.querySelector('[data-navbar]') || document.querySelector('[data-navbar]');
  if (!navbar || navbar.dataset.navbarBound) return;
  navbar.dataset.navbarBound = '1';

  const toggle = navbar.querySelector('[data-navbar-toggle]');
  const panel = navbar.querySelector('[data-navbar-drawer]');
  const scrim = navbar.querySelector('[data-navbar-scrim]');
  const closeBtn = navbar.querySelector('[data-navbar-close]');
  if (!toggle || !panel) return;

  const setOpen = (open) => {
    if (open) {
      panel.hidden = false;
      panel.removeAttribute('hidden');
      panel.classList.add('is-open');
      if (scrim) {
        scrim.hidden = false;
        scrim.removeAttribute('hidden');
        scrim.classList.add('is-open');
      }
      toggle.setAttribute('aria-expanded', 'true');
      document.body.classList.add('navbar-panel-open');
      // Allow CSS transition from off-screen
      requestAnimationFrame(() => {
        panel.classList.add('is-visible');
        scrim?.classList.add('is-visible');
      });
    } else {
      panel.classList.remove('is-visible');
      scrim?.classList.remove('is-visible');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('navbar-panel-open');
      const finish = () => {
        panel.classList.remove('is-open');
        panel.hidden = true;
        panel.setAttribute('hidden', '');
        if (scrim) {
          scrim.classList.remove('is-open');
          scrim.hidden = true;
          scrim.setAttribute('hidden', '');
        }
      };
      window.setTimeout(finish, 220);
    }
  };

  toggle.addEventListener('click', () => {
    const open = panel.hasAttribute('hidden') || !panel.classList.contains('is-visible');
    setOpen(open);
  });

  closeBtn?.addEventListener('click', () => setOpen(false));
  scrim?.addEventListener('click', () => setOpen(false));

  panel.querySelectorAll('[data-modal-open], [data-navbar-close]').forEach((el) => {
    el.addEventListener('click', () => setOpen(false));
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && panel.classList.contains('is-visible')) {
      setOpen(false);
    }
  });
}

export default { initNavbar };
