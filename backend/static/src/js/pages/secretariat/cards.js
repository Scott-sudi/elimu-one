export function initSecretariatCards(root = document) {
  const page = root.querySelector('[data-page="secretariat-cards"]');
  if (!page || page.dataset.pageBound) return;
  page.dataset.pageBound = '1';
}
