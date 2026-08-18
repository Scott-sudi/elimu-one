export function initTooltipManager(root = document) {
  root.querySelectorAll('[data-bi-chart-expand]').forEach((button) => {
    if (!(button instanceof HTMLButtonElement) || button.dataset.biBound === '1') return;
    button.dataset.biBound = '1';
    button.addEventListener('click', () => {
      const chart = document.querySelector(`[data-bi-chart="${button.dataset.biChartExpand}"]`);
      chart?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      chart?.classList.toggle('bi-chart--focus');
    });
  });
}