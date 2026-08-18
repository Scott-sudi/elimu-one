/**
 * BI year comparisons page.
 */

import { biDomainFetch, filtersFromForm } from './bi-api.js';
import { renderPageCharts, updatePageCharts } from './bi-charts.js';
import { initBiFilters } from './bi-filters.js';

/**
 * @param {HTMLElement} page
 */
export async function initComparisons(page) {
  initBiFilters(page);
  await renderPageCharts(page);

  page.querySelectorAll('[data-bi-refresh-charts]').forEach((btn) => {
    btn.addEventListener('click', async (event) => {
      event.preventDefault();
      const form = page.querySelector('[data-bi-filters]');
      const filters = filtersFromForm(form instanceof HTMLFormElement ? form : null);
      const result = await biDomainFetch('comparisons', 'trends', filters);
      if (result.ok && result.data?.charts) {
        await updatePageCharts(page, result.data.charts);
      } else if (result.error !== 'cancelled') {
        window.location.reload();
      }
    });
  });
}

export default { initComparisons };
