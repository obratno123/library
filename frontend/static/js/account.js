document.addEventListener('DOMContentLoaded', async function () {
  if (!window.AuthAPI) return;

  const usernameNodes = document.querySelectorAll('[data-auth="username"]');
  const emailNodes = document.querySelectorAll('[data-auth="email"]');
  const logoutButton = document.getElementById('logout-btn');
  const guestOnly = document.querySelectorAll('[data-auth-guest-only]');

  try {
    const profile = await AuthAPI.apiFetch('/profile/', {
      method: 'GET'
    });

    AuthAPI.saveAuthUser({
      user_id: profile.user_id,
      username: profile.username,
      email: profile.email
    });

    usernameNodes.forEach((node) => {
      node.textContent = profile.username || 'Пользователь';
    });

    emailNodes.forEach((node) => {
      node.textContent = profile.email || 'Не указан';
    });

    guestOnly.forEach((node) => node.remove());
  } catch (error) {
    AuthAPI.clearAuthUser();
    window.location.href = '/login/';
    return;
  }

  if (logoutButton) {
    logoutButton.addEventListener('click', async function () {
      logoutButton.disabled = true;
      try {
        await AuthAPI.apiFetch('/logout/', { method: 'POST', body: JSON.stringify({}) });
      } catch (error) {
        console.warn(error);
      } finally {
        AuthAPI.clearAuthUser();
        window.location.href = '/login/';
      }
    });
  }
});