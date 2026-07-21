import { initImagePreviews } from '../../components/image-preview.js';

export function initSecretariatStudents(root = document) {
  const page = root.querySelector('[data-page="secretariat-students"]');
  if (!page) return;
  initImagePreviews(page);
}
