document.addEventListener('DOMContentLoaded', function () {
  if (!window.AuthAPI) return;
  const user = AuthAPI.getAuthUser();
  const href = user ? 'account.html' : 'login.html';
  document.querySelectorAll('a[href="login.html"], a[href="account.html"]').forEach((link) => {
    const label = (link.getAttribute('aria-label') || '').toLowerCase();
    const icon = link.textContent.toLowerCase();
    if (label.includes('кабинет') || label.includes('вход') || icon.includes('person')) {
      link.setAttribute('href', href);
    }
  });
});
