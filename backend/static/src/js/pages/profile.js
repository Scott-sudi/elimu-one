/**
 * Profile page — password toggle and form feedback.
 */

import { apiPost, apiPatch } from '../core/api.js';
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

  const profileForm = page.querySelector('[data-profile-form]');
  profileForm?.addEventListener('submit', async (e) => {
    if (profileForm.hasAttribute('hx-post') || profileForm.hasAttribute('hx-patch')) return;
    e.preventDefault();

    const btn = profileForm.querySelector('[type="submit"]');
    setButtonLoading(btn, true, { label: 'Enregistrement…' });

    const action = profileForm.getAttribute('action') || '/profil/';
    const method = (profileForm.getAttribute('method') || 'post').toLowerCase();
    const body = new FormData(profileForm);

    try {
      const result =
        method === 'patch'
          ? await apiPatch(action, body)
          : await apiPost(action, body);

      if (!result.ok) {
        toast.error(result.error || 'Impossible d’enregistrer le profil.');
        return;
      }
      toast.success('Profil mis à jour.');
    } finally {
      setButtonLoading(btn, false);
    }
  });

  const passwordForm = page.querySelector('[data-password-form]');
  passwordForm?.addEventListener('submit', async (e) => {
    if (passwordForm.hasAttribute('hx-post')) return;
    e.preventDefault();

    const btn = passwordForm.querySelector('[type="submit"]');
    const newPass = passwordForm.querySelector('[name="new_password1"], [name="new_password"]')?.value;
    const confirm = passwordForm.querySelector('[name="new_password2"], [name="confirm_password"]')?.value;

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
    } finally {
      setButtonLoading(btn, false);
    }
  });
}

export default { initProfile };
