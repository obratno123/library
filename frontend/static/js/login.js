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
      const data = await AuthAPI.apiFetch('/login/', {
        method: 'POST',
        body: JSON.stringify({
          username: usernameInput.value.trim(),
          password: passwordInput.value
        })
      });

      AuthAPI.saveAuthUser({
        user_id: data.user_id,
        username: data.username,
        email: usernameInput.value.trim()
      });

      AuthAPI.setMessage(message, data.message || 'Вход выполнен', false);
      window.location.href = '/profile/';
    } catch (error) {
      AuthAPI.setMessage(message, error.message || 'Ошибка входа', true);
    } finally {
      submitButton.disabled = false;
    }
  });
});
