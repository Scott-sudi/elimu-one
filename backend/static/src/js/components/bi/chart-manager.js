/**
 * Plotly chart lifecycle: render, react, empty state, resize.
 */

import Plotly from 'plotly.js-dist-min';
import {
  BI_COLORS,
  defaultPlotlyConfig,
  defaultPlotlyLayout,
  paletteColor,
} from './plotly-config.js';

const EMPTY_CLASS = 'bi-chart__empty';
const BOUND_ATTR = 'data-bi-chart-bound';

/** @type {WeakMap<HTMLElement, ResizeObserver>} */
const observers = new WeakMap();

/**
 * @param {unknown} value
 * @returns {number}
 */
function toNumber(value) {
  if (value == null || value === '') return 0;
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

/**
 * @param {{ labels?: unknown[], series?: { name?: string, data?: unknown[] }[] } | null | undefined} payload
 * @returns {boolean}
 */
export function isChartEmpty(payload) {
  if (!payload || typeof payload !== 'object') return true;
  const labels = Array.isArray(payload.labels) ? payload.labels : [];
  const series = Array.isArray(payload.series) ? payload.series : [];
  if (!labels.length || !series.length) return true;
  const hasValue = series.some((s) =>
    (Array.isArray(s?.data) ? s.data : []).some((v) => toNumber(v) !== 0),
  );
  return !hasValue && labels.every((l) => l == null || String(l).trim() === '');
}

/**
 * @param {HTMLElement} el
 * @param {string} [message]
 */
export function showEmptyState(el, message = 'Aucune donnée à afficher pour ces filtres.') {
  el.classList.add('bi-chart--empty');
  let empty = el.querySelector(`.${EMPTY_CLASS}`);
  if (!empty) {
    empty = document.createElement('div');
    empty.className = EMPTY_CLASS;
    empty.setAttribute('role', 'status');
    el.appendChild(empty);
  }
  empty.hidden = false;
  empty.textContent = message;
  if (el.data?.length || el._fullLayout) {
    try {
      Plotly.purge(el);
    } catch {
      /* ignore */
    }
  }
}

/**
 * @param {HTMLElement} el
 */
export function hideEmptyState(el) {
  el.classList.remove('bi-chart--empty');
  const empty = el.querySelector(`.${EMPTY_CLASS}`);
  if (empty) empty.hidden = true;
}

/**
 * Build Plotly traces from server chart payload { labels, series }.
 * @param {{ labels?: unknown[], series?: { name?: string, data?: unknown[] }[] }} payload
 * @param {'bar' | 'line' | 'pie' | 'donut' | 'hbar'} [type='bar']
 * @returns {object[]}
 */
export function buildTraces(payload, type = 'bar') {
  const labels = (payload.labels || []).map((l) => (l == null ? '' : String(l)));
  const series = Array.isArray(payload.series) ? payload.series : [];

  if (type === 'pie' || type === 'donut') {
    const first = series[0] || { data: [] };
    const values = (first.data || []).map(toNumber);
    return [
      {
        type: 'pie',
        labels,
        values,
        hole: type === 'donut' ? 0.45 : 0,
        marker: {
          colors: labels.map((_, i) => paletteColor(i)),
          line: { color: BI_COLORS.surface, width: 1 },
        },
        textinfo: 'label+percent',
        hovertemplate: '%{label}<br>%{value}<br>%{percent}<extra></extra>',
        sort: false,
      },
    ];
  }

  return series.map((s, index) => {
    const y = (s.data || []).map(toNumber);
    const name = s.name || `Série ${index + 1}`;
    const color = paletteColor(index);

    if (type === 'line') {
      return {
        type: 'scatter',
        mode: 'lines+markers',
        name,
        x: labels,
        y,
        line: { color, width: 2 },
        marker: { color, size: 6 },
        hovertemplate: `%{x}<br>${name}: %{y}<extra></extra>`,
      };
    }

    if (type === 'hbar') {
      return {
        type: 'bar',
        orientation: 'h',
        name,
        y: labels,
        x: y,
        marker: { color },
        hovertemplate: `%{y}<br>${name}: %{x}<extra></extra>`,
      };
    }

    return {
      type: 'bar',
      name,
      x: labels,
      y,
      marker: { color },
      hovertemplate: `%{x}<br>${name}: %{y}<extra></extra>`,
    };
  });
}

/**
 * @param {'bar' | 'line' | 'pie' | 'donut' | 'hbar'} type
 * @param {Record<string, unknown>} [layoutOverrides]
 */
function layoutForType(type, layoutOverrides = {}) {
  if (type === 'pie' || type === 'donut') {
    return defaultPlotlyLayout({
      showlegend: true,
      margin: { l: 24, r: 24, t: 24, b: 24 },
      ...layoutOverrides,
    });
  }
  if (type === 'hbar') {
    return defaultPlotlyLayout({
      margin: { l: 96, r: 24, t: 36, b: 40 },
      ...layoutOverrides,
    });
  }
  return defaultPlotlyLayout(layoutOverrides);
}

/**
 * @param {HTMLElement} el
 */
function ensureResize(el) {
  if (observers.has(el) || typeof ResizeObserver === 'undefined') return;
  const ro = new ResizeObserver(() => {
    if (!el.isConnected) return;
    try {
      Plotly.Plots.resize(el);
    } catch {
      /* ignore */
    }
  });
  ro.observe(el);
  observers.set(el, ro);
  el.setAttribute(BOUND_ATTR, '1');
}

/**
 * Render or update a chart from a server payload.
 * @param {HTMLElement} el
 * @param {{ labels?: unknown[], series?: { name?: string, data?: unknown[] }[] } | null | undefined} payload
 * @param {{ type?: 'bar' | 'line' | 'pie' | 'donut' | 'hbar', layout?: Record<string, unknown>, emptyMessage?: string }} [options]
 * @returns {Promise<void>}
 */
export async function renderChart(el, payload, options = {}) {
  const type = options.type || el.getAttribute('data-bi-chart-type') || 'bar';
  const emptyMessage =
    options.emptyMessage ||
    el.getAttribute('data-bi-empty') ||
    'Aucune donnée à afficher pour ces filtres.';

  if (isChartEmpty(payload)) {
    showEmptyState(el, emptyMessage);
    return;
  }

  hideEmptyState(el);
  const data = buildTraces(payload, /** @type {any} */ (type));
  const layout = layoutForType(/** @type {any} */ (type), options.layout || {});
  const config = { ...defaultPlotlyConfig };

  if (el.getAttribute(BOUND_ATTR) === '1' || el.data) {
    await Plotly.react(el, data, layout, config);
  } else {
    await Plotly.newPlot(el, data, layout, config);
  }
  ensureResize(el);
}

/**
 * Purge chart and detach resize observer.
 * @param {HTMLElement} el
 */
export function destroyChart(el) {
  const ro = observers.get(el);
  if (ro) {
    ro.disconnect();
    observers.delete(el);
  }
  el.removeAttribute(BOUND_ATTR);
  try {
    Plotly.purge(el);
  } catch {
    /* ignore */
  }
}

/**
 * Resize all bound charts under a root.
 * @param {ParentNode} [root=document]
 */
export function resizeCharts(root = document) {
  root.querySelectorAll(`[data-bi-chart][${BOUND_ATTR}]`).forEach((el) => {
    if (!(el instanceof HTMLElement)) return;
    try {
      Plotly.Plots.resize(el);
    } catch {
      /* ignore */
    }
  });
}

export default {
  isChartEmpty,
  showEmptyState,
  hideEmptyState,
  buildTraces,
  renderChart,
  destroyChart,
  resizeCharts,
};
