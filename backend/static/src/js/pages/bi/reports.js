/**
 * BI reports page — chart preview + export links (server-rendered).
 */

import { renderPageCharts } from './bi-charts.js';

/**
 * @param {HTMLElement} page
 */
export async function initReports(page) {
  await renderPageCharts(page);
}

export default { initReports };
