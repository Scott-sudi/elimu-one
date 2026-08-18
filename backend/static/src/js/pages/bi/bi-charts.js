/**
 * Resolve chart payloads from json_script and render Plotly charts.
 */

import { renderChart, resizeCharts } from '../../components/bi/chart-manager.js';

/**
 * Map data-bi-chart attribute to payload key.
 * e.g. enrollments-trend → trend, enrollments-by-class → by_class
 * @param {string} attr
 * @returns {string}
 */
export function chartKeyFromAttr(attr) {
  if (!attr) return '';
  if (!attr.includes('-')) return attr;
  const rest = attr.slice(attr.indexOf('-') + 1);
  return rest.replace(/-/g, '_');
}

/**
 * Infer chart type when data-bi-chart-type is absent.
 * @param {string} key
 * @returns {'bar' | 'line' | 'pie' | 'donut' | 'hbar'}
 */
export function inferChartType(key) {
  if (['trend', 'collections', 'late'].includes(key)) return 'line';
  if (['status', 'by_gender', 'by_method', 'exports'].includes(key)) return 'donut';
  if (['recovery', 'summons', 'severity'].includes(key)) return 'hbar';
  return 'bar';
}

/**
 * @param {ParentNode} [root=document]
 * @returns {Record<string, any> | null}
 */
export function readChartsPayload(root = document) {
  const script =
    (root instanceof Element ? root.closest('main, body') : null)?.querySelector(
      '#bi-charts-data',
    ) ||
    document.getElementById('bi-charts-data');
  if (!script) return null;
  try {
    return JSON.parse(script.textContent || '{}');
  } catch {
    return null;
  }
}

/**
 * @param {ParentNode} root
 * @param {Record<string, any> | null | undefined} charts
 * @returns {Promise<void>}
 */
export async function renderPageCharts(root, charts) {
  const payload = charts || readChartsPayload(root) || {};
  const nodes = root.querySelectorAll('[data-bi-chart]');
  const jobs = [];

  nodes.forEach((node) => {
    if (!(node instanceof HTMLElement)) return;
    const attr = node.getAttribute('data-bi-chart') || '';
    const key = chartKeyFromAttr(attr);
    const typeAttr = node.getAttribute('data-bi-chart-type');
    const type = /** @type {any} */ (typeAttr || inferChartType(key));
    const data = payload[key] ?? payload[attr] ?? null;
    jobs.push(renderChart(node, data, { type }));
  });

  await Promise.all(jobs);
}

/**
 * Replace charts payload and re-render.
 * @param {ParentNode} root
 * @param {Record<string, any>} charts
 * @returns {Promise<void>}
 */
export async function updatePageCharts(root, charts) {
  const script = document.getElementById('bi-charts-data');
  if (script) {
    script.textContent = JSON.stringify(charts || {});
  }
  await renderPageCharts(root, charts);
}

export { resizeCharts };

export default {
  chartKeyFromAttr,
  inferChartType,
  readChartsPayload,
  renderPageCharts,
  updatePageCharts,
  resizeCharts,
};
