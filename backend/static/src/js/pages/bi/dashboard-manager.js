import { renderChart } from '../../components/bi/chart-manager.js';
import { biDomainFetch } from './bi-api.js';
import { getFilters } from './filter-manager.js';
import { applyClassFilter, bindClassDrilldown } from './drilldown-manager.js';

const requests = [
  ['enrollmentsSummary', 'enrollments', 'summary'],
  ['enrollmentsTrends', 'enrollments', 'trends'],
  ['financialSummary', 'financial', 'summary'],
  ['financialTrends', 'financial', 'trends'],
  ['attendanceSummary', 'attendance', 'summary'],
  ['attendanceTrends', 'attendance', 'trends'],
  ['disciplineSummary', 'discipline', 'summary'],
  ['disciplineTrends', 'discipline', 'trends'],
  ['classes', 'classes', 'classes'],
];

function value(value, suffix = '') {
  return value == null ? '—' : `${value}${suffix}`;
}

function setKpi(page, key, nextValue) {
  const target = page.querySelector(`[data-bi-kpi="${key}"]`);
  if (target) target.textContent = value(nextValue);
}

function setClassTable(page, rows) {
  const body = page.querySelector('[data-bi-class-table]');
  if (!body) return;
  body.replaceChildren();
  if (!rows.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.textContent = 'Aucune donnée de classe pour ces filtres.';
    row.append(cell);
    body.append(row);
    return;
  }
  rows.slice(0, 8).forEach((item) => {
    const row = document.createElement('tr');
    row.dataset.biClassId = item.class_id;
    [item.name, item.effectif ?? '—', value(item.taux_occupation, ' %'), value(item.taux_presence, ' %'), item.incidents_ouverts ?? '—'].forEach((cellValue) => {
      const cell = document.createElement('td');
      cell.textContent = String(cellValue);
      row.append(cell);
    });
    body.append(row);
  });
  body.querySelectorAll('[data-bi-class-id]').forEach((row) => row.addEventListener('click', () => {
    const classId = row.dataset.biClassId;
    if (classId && !applyClassFilter(classId)) {
      window.location.assign(`${page.dataset.biClassesUrl}?class_id=${encodeURIComponent(classId)}`);
    }
  }));
}

async function render(page, filters = {}) {
  page.classList.add('bi-page--loading');
  const results = await Promise.all(requests.map(async ([key, domain, section]) => {
    const response = await biDomainFetch(domain, section, filters);
    return [key, response.ok ? response.data : null];
  }));
  const data = Object.fromEntries(results);
  const enrollmentSummary = data.enrollmentsSummary || {};
  const enrollmentTrends = data.enrollmentsTrends || {};
  const financialSummary = data.financialSummary || {};
  const financialTrends = data.financialTrends || {};
  const attendanceSummary = data.attendanceSummary || {};
  const attendanceTrends = data.attendanceTrends || {};
  const disciplineSummary = data.disciplineSummary || {};
  const disciplineTrends = data.disciplineTrends || {};
  const classes = data.classes || {};
  const charts = {
    'finance-collections': financialTrends.charts?.collections,
    'attendance-status': attendanceTrends.charts?.status,
    'enrollments-by-class': enrollmentTrends.charts?.by_class,
    'discipline-by-class': disciplineTrends.charts?.by_class,
    'attendance-by-class': attendanceTrends.charts?.by_class,
  };
  await Promise.all(Object.entries(charts).map(async ([key, payload]) => {
    const chart = page.querySelector(`[data-bi-chart="${key}"]`);
    if (chart) await renderChart(chart, payload);
  }));
  setKpi(page, 'effectif_total', enrollmentSummary.kpis?.effectif_total);
  setKpi(page, 'taux_recouvrement', financialSummary.kpis?.taux_recouvrement);
  setKpi(page, 'taux_presence', attendanceSummary.kpis?.taux_presence);
  setKpi(page, 'incidents_ouverts', disciplineSummary.kpis?.incidents_ouverts);
  const rows = classes.tables?.classes || [];
  setClassTable(page, rows);
  bindClassDrilldown(page.querySelector('[data-bi-chart="enrollments-by-class"]'), classes.tables?.classes || [], page.dataset.biClassesUrl);
  bindClassDrilldown(page.querySelector('[data-bi-chart="discipline-by-class"]'), classes.tables?.classes || [], page.dataset.biClassesUrl);
  bindClassDrilldown(page.querySelector('[data-bi-chart="attendance-by-class"]'), classes.tables?.classes || [], page.dataset.biClassesUrl);
  page.classList.remove('bi-page--loading');
}

export function initDashboardManager(page) {
  if (!(page instanceof HTMLElement) || page.dataset.biDashboardBound === '1') return;
  page.dataset.biDashboardBound = '1';
  const refresh = () => render(page, getFilters()).catch((error) => console.error('[BI] Dashboard refresh failed', error));
  document.addEventListener('bi:filters-change', refresh);
  page.querySelectorAll('[data-bi-refresh]').forEach((button) => button.addEventListener('click', refresh));
  refresh();
}