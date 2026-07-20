/**
 * Login page — async POST to /connexion/.
 */

import { apiPost } from '../core/api.js';
import { toast } from '../core/notifications.js';
import { setButtonLoading } from '../core/loading.js';

const LOGIN_URL = '/connexion/';

/**
 * @param {ParentNode} [root=document]
 */
export function initLogin(root = document) {
  const form = root.querySelector('[data-login-form]') || root.querySelector('#login-form');
  if (!form || form.dataset.loginBound) return;
  form.dataset.loginBound = '1';

  const submitBtn =
    form.querySelector('[type="submit"]') ||
    form.querySelector('[data-login-submit]');
  const errorBox = form.querySelector('[data-login-error]');

  const clearError = () => {
    if (errorBox) {
      errorBox.hidden = true;
      errorBox.textContent = '';
    }
  };

  /**
   * @param {string} message
   */
  const showError = (message) => {
    if (errorBox) {
      errorBox.hidden = false;
      errorBox.textContent = message;
    }
    toast.error(message);
  };

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const username =
      form.querySelector('[name="username"], [name="email"], [data-login-username]')
        ?.value?.trim() || '';
    const password =
      form.querySelector('[name="password"], [data-login-password]')?.value || '';

    if (!username || !password) {
      showError('Veuillez renseigner vos identifiants.');
      return;
    }

    setButtonLoading(submitBtn, true, { label: 'Connexion…' });

    try {
      const prefersJson =
        form.getAttribute('data-login-json') !== 'false' &&
        form.enctype !== 'application/x-www-form-urlencoded';

      let result;
      if (prefersJson) {
        result = await apiPost(LOGIN_URL, { username, password });
      } else {
        const body = new FormData(form);
        if (!body.has('username') && username) body.set('username', username);
        if (!body.has('password') && password) body.set('password', password);
        result = await apiPost(LOGIN_URL, body);
      }

      if (!result.ok) {
        showError(result.error || 'Identifiants incorrects.');
        return;
      }

      const redirect =
        result.data?.redirect ||
        result.data?.redirect_url ||
        form.getAttribute('data-login-redirect') ||
        '/tableau-de-bord/';

      toast.success('Connexion réussie.');
      window.location.assign(redirect);
    } catch {
      showError('Impossible de se connecter. Réessayez.');
    } finally {
      setButtonLoading(submitBtn, false);
    }
  });

  form.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const tag = e.target?.tagName?.toLowerCase();
    if (tag === 'textarea') return;
    e.preventDefault();
    if (typeof form.requestSubmit === 'function') {
      form.requestSubmit(submitBtn || undefined);
    } else {
      form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }
  });
}

export default { initLogin };
