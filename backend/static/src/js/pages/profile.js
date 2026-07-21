/**
 * Profile page — password toggle and form feedback.
 */

import { apiPost } from '../core/api.js';
import { toast } from '../core/notifications.js';
import { setButtonLoading } from '../core/loading.js';
import { initPasswordToggles } from '../components/password-toggle.js';

/**
 * @param {ParentNode} [root=document]
 */
export function initProfile(root = document) {
  const page = root.querySelector('[data-page="profile"]') || root.querySelector('[data-profile-page]');
  if (!page || page.dataset.profileBound) return;
  page.dataset.profileBound = '1';

  initPasswordToggles(page);
  initProfilePhoto(page);

  const passwordForm = page.querySelector('[data-password-form]');
  passwordForm?.addEventListener('submit', async (e) => {
    if (passwordForm.hasAttribute('hx-post')) return;
    e.preventDefault();

    const btn = passwordForm.querySelector('[type="submit"]');
    const newPass = passwordForm.querySelector('[name="new_password"], [name="new_password1"]')?.value;
    const confirm = passwordForm.querySelector('[name="new_password_confirm"], [name="new_password2"], [name="confirm_password"]')?.value;

    if (newPass && confirm && newPass !== confirm) {
      toast.error('Les mots de passe ne correspondent pas.');
      return;
    }

    setButtonLoading(btn, true, { label: 'Mise à jour…' });
    try {
      const action = passwordForm.getAttribute('action') || '/profil/mot-de-passe/';
      const result = await apiPost(action, new FormData(passwordForm));
      if (!result.ok) {
        toast.error(result.error || 'Impossible de changer le mot de passe.');
        return;
      }
      passwordForm.reset();
      toast.success('Mot de passe mis à jour.');
      // Reload so the forced-change middleware releases navigation.
      window.setTimeout(() => { window.location.href = '/tableau-de-bord/'; }, 600);
    } finally {
      setButtonLoading(btn, false);
    }
  });
}

function initProfilePhoto(page) {
  const input = page.querySelector('[data-profile-photo-input]');
  const selectButton = page.querySelector('[data-profile-photo-select]');
  const cameraButton = page.querySelector('[data-profile-camera-open]');
  const camera = page.querySelector('[data-profile-camera]');
  const video = page.querySelector('[data-profile-camera-video]');
  const canvas = page.querySelector('[data-profile-camera-canvas]');
  const captureButton = page.querySelector('[data-profile-camera-capture]');
  const cancelButton = page.querySelector('[data-profile-camera-cancel]');
  const avatarImage = page.querySelector('[data-profile-avatar-image]');
  const avatarInitials = page.querySelector('[data-profile-avatar-initials]');
  let stream;

  const stopCamera = () => {
    stream?.getTracks().forEach((track) => track.stop());
    stream = undefined;
    if (video) video.srcObject = null;
    if (camera) camera.hidden = true;
  };

  const previewFile = (file) => {
    if (!file || !avatarImage) return;
    avatarImage.src = URL.createObjectURL(file);
    avatarImage.hidden = false;
    avatarInitials?.setAttribute('hidden', '');
  };

  selectButton?.addEventListener('click', () => input?.click());
  input?.addEventListener('change', () => previewFile(input.files?.[0]));

  cameraButton?.addEventListener('click', async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error('La caméra n’est pas prise en charge par ce navigateur.');
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      if (video) video.srcObject = stream;
      if (camera) camera.hidden = false;
    } catch {
      toast.error('Autorisez l’accès à la caméra pour prendre une photo.');
    }
  });

  captureButton?.addEventListener('click', () => {
    if (!video || !canvas || !input || !video.videoWidth || !video.videoHeight) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const photo = new File([blob], 'photo-profil.jpg', { type: 'image/jpeg' });
      const files = new DataTransfer();
      files.items.add(photo);
      input.files = files.files;
      previewFile(photo);
      stopCamera();
    }, 'image/jpeg', 0.9);
  });

  cancelButton?.addEventListener('click', stopCamera);
  window.addEventListener('pagehide', stopCamera, { once: true });
}

export default { initProfile };
