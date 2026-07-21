export function initSecretariatDocuments(root = document) {
  const page = root.querySelector('[data-page="secretariat-documents"]');
  if (!page || page.dataset.pageBound) return;
  page.dataset.pageBound = '1';
}
