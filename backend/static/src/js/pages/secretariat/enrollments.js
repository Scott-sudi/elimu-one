import { initEnrollmentWizard } from '../../components/enrollment-wizard.js';

export function initSecretariatEnrollments(root = document) {
  if (!root.querySelector('[data-page="secretariat-enrollments"]')) return;
  initEnrollmentWizard(root);
}
