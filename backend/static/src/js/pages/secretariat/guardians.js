export function initSecretariatGuardians(root = document) {
  const page = root.querySelector('[data-page="secretariat-guardians"]');
  if (!page || page.dataset.pageBound) return;
  page.dataset.pageBound = '1';
}
