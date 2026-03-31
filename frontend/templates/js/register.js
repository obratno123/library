document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('register-form');
  if (!form || !window.AuthAPI) return;

  const usernameInput = document.getElementById('register-username');
  const emailInput = document.getElementById('register-email');
  const passwordInput = document.getElementById('register-password');
  const confirmInput = document.getElementById('register-password-confirm');
  const message = document.getElementById('register-message');
  const submitButton = document.getElementById('register-submit');

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    AuthAPI.setMessage(message, '', true);

    const username = usernameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const passwordConfirm = confirmInput.value;

    if (password !== passwordConfirm) {
      AuthAPI.setMessage(message, 'Пароли не совпадают', true);
      return;
    }

    submitButton.disabled = true;

    try {
      const data = await AuthAPI.apiFetch('/register/', {
        method: 'POST',
        body: JSON.stringify({ username, email, password })
      });

      AuthAPI.saveAuthUser({
        user_id: data.user_id,
        username: data.username || username,
        email
      });

      AuthAPI.setMessage(message, data.message || 'Аккаунт создан', false);
      window.location.href = 'account.html';
    } catch (error) {
      AuthAPI.setMessage(message, error.message || 'Ошибка регистрации', true);
    } finally {
      submitButton.disabled = false;
    }
  });
});
