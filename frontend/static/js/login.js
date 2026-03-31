document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('login-form');
  if (!form || !window.AuthAPI) return;

  const usernameInput = document.getElementById('login-username');
  const passwordInput = document.getElementById('login-password');
  const message = document.getElementById('login-message');
  const submitButton = document.getElementById('login-submit');
  const togglePassword = document.querySelector('[data-toggle-password="login-password"]');

  if (togglePassword) {
    togglePassword.addEventListener('click', function () {
      passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password';
    });
  }

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    AuthAPI.setMessage(message, '', true);
    submitButton.disabled = true;

    try {
      await AuthAPI.apiFetch('/login/', {
        method: 'POST',
        body: JSON.stringify({
          username: usernameInput.value.trim(),
          password: passwordInput.value
        })
      });

      const profile = await AuthAPI.apiFetch('/profile/', {
        method: 'GET'
      });

      AuthAPI.saveAuthUser({
        user_id: profile.user_id,
        username: profile.username,
        email: profile.email
      });

      AuthAPI.setMessage(message, 'Вход выполнен', false);
      window.location.href = '/profile/';
    } catch (error) {
      AuthAPI.setMessage(message, error.message || 'Ошибка входа', true);
    } finally {
      submitButton.disabled = false;
    }
  });
});