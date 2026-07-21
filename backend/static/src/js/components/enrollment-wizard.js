export function initEnrollmentWizard(root = document) {
  const wizard = root.querySelector('[data-enrollment-wizard]');
  if (!wizard || wizard.dataset.wizardBound) return;
  wizard.dataset.wizardBound = '1';
  wizard.querySelectorAll('select').forEach((select) => {
    select.addEventListener('change', () => wizard.dispatchEvent(new CustomEvent('wizard:change')));
  });
}
