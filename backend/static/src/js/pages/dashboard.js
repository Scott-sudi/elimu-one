/**
 * Dashboard page enhancements.
 */

/**
 * @param {ParentNode} [root=document]
 */
export function initDashboard(root = document) {
  const page = root.querySelector('[data-page="dashboard"]');
  if (!page || page.dataset.dashboardBound) return;
  page.dataset.dashboardBound = '1';

  page.querySelectorAll('[data-dashboard-refresh]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.getAttribute('data-dashboard-refresh');
      if (target && window.htmx) {
        window.htmx.trigger(target, 'refresh');
      } else {
        window.location.reload();
      }
    });
  });

  document.dispatchEvent(new CustomEvent('kalunga:dashboard-ready', { detail: { root: page } }));
}

export default { initDashboard };
