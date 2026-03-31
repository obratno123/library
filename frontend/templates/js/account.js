document.addEventListener('DOMContentLoaded', function () {
  if (!window.AuthAPI) return;

  const user = AuthAPI.getAuthUser();
  const usernameNodes = document.querySelectorAll('[data-auth="username"]');
  const emailNodes = document.querySelectorAll('[data-auth="email"]');
  const logoutButton = document.getElementById('logout-btn');
  const guestOnly = document.querySelectorAll('[data-auth-guest-only]');

  if (!user) {
    window.location.href = 'login.html';
    return;
  }

  usernameNodes.forEach((node) => {
    node.textContent = user.username || 'Пользователь';
  });

  emailNodes.forEach((node) => {
    node.textContent = user.email || 'Не указан';
  });

  guestOnly.forEach((node) => node.remove());

  if (logoutButton) {
    logoutButton.addEventListener('click', async function () {
      logoutButton.disabled = true;
      try {
        await AuthAPI.apiFetch('/logout/', { method: 'POST', body: JSON.stringify({}) });
      } catch (error) {
        console.warn(error);
      } finally {
        AuthAPI.clearAuthUser();
        window.location.href = 'login.html';
      }
    });
  }
});
