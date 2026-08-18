/**
 * Shared Plotly defaults and Kalunga palette for BI charts.
 * Colors mirror tokens/colors.css — no decorative gradients.
 */

/** @type {ReadonlyArray<string>} */
export const BI_PALETTE = Object.freeze([
  '#0d5a22', // primary
  '#167033', // success / secondary green
  '#3f76b5', // information
  '#c4922e', // warning
  '#c0392b', // danger
  '#6b736e', // text secondary / neutral
  '#9aa39c', // disabled / inactive
  '#1a1f1c', // text primary
  '#c7dfcb', // primary muted
  '#073c16', // primary dark
]);

export const BI_COLORS = Object.freeze({
  primary: '#0d5a22',
  success: '#167033',
  information: '#3f76b5',
  warning: '#c4922e',
  danger: '#c0392b',
  neutral: '#6b736e',
  muted: '#9aa39c',
  text: '#1a1f1c',
  grid: '#e4e4e0',
  border: '#dcdfd9',
  surface: '#ffffff',
  soft: '#e6f2e8',
});

/**
 * Plotly config passed as the third argument to newPlot / react.
 * @type {Partial<Plotly.Config>}
 */
export const defaultPlotlyConfig = Object.freeze({
  responsive: true,
  displaylogo: false,
  scrollZoom: false,
  displayModeBar: true,
  modeBarButtonsToRemove: [
    'lasso2d',
    'select2d',
    'autoScale2d',
    'hoverClosestCartesian',
    'hoverCompareCartesian',
    'toggleSpikelines',
  ],
  locale: 'fr',
});

/**
 * Base layout merged into every chart.
 * @param {Record<string, unknown>} [overrides={}]
 * @returns {Record<string, unknown>}
 */
export function defaultPlotlyLayout(overrides = {}) {
  return {
    autosize: true,
    paper_bgcolor: BI_COLORS.surface,
    plot_bgcolor: BI_COLORS.surface,
    font: {
      family: 'Segoe UI, system-ui, sans-serif',
      size: 12,
      color: BI_COLORS.text,
    },
    margin: { l: 48, r: 24, t: 36, b: 48 },
    colorway: [...BI_PALETTE],
    legend: {
      orientation: 'h',
      yanchor: 'bottom',
      y: 1.02,
      xanchor: 'left',
      x: 0,
      font: { size: 11, color: BI_COLORS.neutral },
    },
    xaxis: {
      automargin: true,
      gridcolor: BI_COLORS.grid,
      linecolor: BI_COLORS.border,
      zerolinecolor: BI_COLORS.border,
      tickfont: { color: BI_COLORS.neutral },
      title: { font: { color: BI_COLORS.neutral, size: 11 } },
    },
    yaxis: {
      automargin: true,
      gridcolor: BI_COLORS.grid,
      linecolor: BI_COLORS.border,
      zerolinecolor: BI_COLORS.border,
      tickfont: { color: BI_COLORS.neutral },
      title: { font: { color: BI_COLORS.neutral, size: 11 } },
    },
    hoverlabel: {
      bgcolor: BI_COLORS.surface,
      bordercolor: BI_COLORS.border,
      font: { color: BI_COLORS.text, size: 12 },
    },
    ...overrides,
  };
}

/**
 * Pick a palette color by series index.
 * @param {number} index
 * @returns {string}
 */
export function paletteColor(index) {
  return BI_PALETTE[index % BI_PALETTE.length];
}

export default {
  BI_PALETTE,
  BI_COLORS,
  defaultPlotlyConfig,
  defaultPlotlyLayout,
  paletteColor,
};
