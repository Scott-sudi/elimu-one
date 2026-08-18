/**
 * BI module boot — dispatches to page initializers via data-page.
 */

import { initFilterManager } from './filter-manager.js';
import { initTooltipManager } from './tooltip-manager.js';
import { initExportManager } from './export-manager.js';

const PAGE_INIT = {
  'bi-overview': () => import('./overview.js').then((module) => module.initOverview),
  'bi-enrollments': () => import('./enrollments.js').then((module) => module.initEnrollments),
  'bi-finance': () => import('./finance.js').then((module) => module.initFinance),
  'bi-attendance': () => import('./attendance.js').then((module) => module.initAttendance),
  'bi-discipline': () => import('./discipline.js').then((module) => module.initDiscipline),
  'bi-classes': () => import('./classes.js').then((module) => module.initClasses),
  'bi-comparisons': () => import('./comparisons.js').then((module) => module.initComparisons),
  'bi-reports': () => import('./reports.js').then((module) => module.initReports),
};

let resizeBound = false;

/**
 * @param {ParentNode} [root=document]
 */
export function initBi(root = document) {
  initFilterManager(root);
  initTooltipManager(root);
  initExportManager(root);
  if (root === document && document.body.dataset.biGlobalFiltersBound !== '1') {
    document.body.dataset.biGlobalFiltersBound = '1';
    document.addEventListener('bi:filters-change', () => {
      if (!document.querySelector('[data-page="bi-overview"]')) {
        window.location.assign(window.location.href);
      }
    });
  }
  Object.entries(PAGE_INIT).forEach(([pageId, loadPage]) => {
    const page = root.querySelector(`[data-page="${pageId}"]`);
    if (!(page instanceof HTMLElement) || page.dataset.biBound === '1') return;
    page.dataset.biBound = '1';
    loadPage().then((initPage) => initPage(page)).catch((err) => {
      console.error(`[BI] Failed to init ${pageId}`, err);
    });
  });

  if (!resizeBound) {
    resizeBound = true;
    window.addEventListener('resize', () => {
      import('./bi-charts.js').then(({ resizeCharts }) => resizeCharts(document));
    });
  }

  root.querySelectorAll('[data-bi-sidebar-toggle]').forEach((button) => {
    if (!(button instanceof HTMLButtonElement) || button.dataset.biBound === '1') return;
    button.dataset.biBound = '1';
    button.addEventListener('click', () => document.body.classList.toggle('bi-sidebar-open'));
  });
}

export default { initBi };
