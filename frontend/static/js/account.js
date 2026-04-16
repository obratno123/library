document.addEventListener('DOMContentLoaded', async function () {
  if (!window.AuthAPI) return;

  const usernameNodes = document.querySelectorAll('[data-auth="username"]');
  const emailNodes = document.querySelectorAll('[data-auth="email"]');
  const avatarNode = document.getElementById('profile-avatar');
  const verifiedBadge = document.getElementById('email-verified-badge');
  const unverifiedBadge = document.getElementById('email-unverified-badge');
  const verifyEmailBtn = document.getElementById('verify-email-btn');
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
      node.textContent = profile.full_name || profile.username || 'Пользователь';
    });

    emailNodes.forEach((node) => {
      node.textContent = profile.email || 'Не указан';
    });

    if (avatarNode) {
      if (profile.avatar_url) {
        avatarNode.src = `${profile.avatar_url}?v=${Date.now()}`;
      } else {
        avatarNode.src = '/static/img/default-avatar.png';
      }
    }

    if (profile.is_email_verified) {
      if (verifiedBadge) verifiedBadge.classList.remove('hidden');
      if (verifiedBadge) verifiedBadge.classList.add('inline-flex');

      if (unverifiedBadge) unverifiedBadge.classList.add('hidden');
      if (verifyEmailBtn) verifyEmailBtn.classList.add('hidden');
    } else {
      if (unverifiedBadge) unverifiedBadge.classList.remove('hidden');
      if (unverifiedBadge) unverifiedBadge.classList.add('inline-flex');

      if (verifiedBadge) verifiedBadge.classList.add('hidden');

      if (verifyEmailBtn) verifyEmailBtn.classList.remove('hidden');
      if (verifyEmailBtn) verifyEmailBtn.classList.add('inline-flex');
    }

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
        await AuthAPI.apiFetch('/logout/', {
          method: 'POST',
          body: JSON.stringify({})
        });
      } catch (error) {
        console.warn(error);
      } finally {
        AuthAPI.clearAuthUser();
        window.location.href = '/login/';
      }
    });
  }
});