export function initImagePreviews(root = document) {
  root.querySelectorAll('[data-image-input]').forEach((input) => {
    if (input.dataset.previewBound) return;
    input.dataset.previewBound = '1';
    input.addEventListener('change', () => {
      const preview = root.querySelector(input.dataset.previewTarget || '[data-image-preview]');
      const file = input.files?.[0];
      if (!preview || !file) return;
      preview.src = URL.createObjectURL(file);
      preview.hidden = false;
    });
  });
}
