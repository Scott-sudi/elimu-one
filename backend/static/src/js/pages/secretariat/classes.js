export function initSecretariatClasses(root = document) {
  const page = root.querySelector('[data-page="secretariat-classes"]');
  if (!page || page.dataset.pageBound) return;
  page.dataset.pageBound = '1';
}
