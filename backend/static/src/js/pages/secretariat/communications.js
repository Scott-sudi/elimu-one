export function initSecretariatCommunications(root = document) {
  const page = root.querySelector('[data-page="secretariat-communications"]');
  if (!page || page.dataset.pageBound) return;
  page.dataset.pageBound = '1';
}
