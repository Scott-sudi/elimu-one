export function initExportManager(root = document) {
  root.querySelectorAll('[data-bi-print]').forEach((button) => {
    if (!(button instanceof HTMLButtonElement) || button.dataset.biBound === '1') return;
    button.dataset.biBound = '1';
    button.addEventListener('click', () => window.print());
  });
}