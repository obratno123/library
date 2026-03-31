(function () {
  const config = window.AUTH_CONFIG || {};
  const API_BASE = (config.API_BASE || '').replace(/\/$/, '');

  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        return decodeURIComponent(cookie.slice(name.length + 1));
      }
    }
    return null;
  }

  function getAuthHeaders(includeJson = true) {
    const headers = {};
    if (includeJson) {
      headers['Content-Type'] = 'application/json';
    }
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
    return headers;
  }

  function buildUrl(path) {
    if (/^https?:\/\//i.test(path)) return path;
    return `${API_BASE}${path.startsWith('/') ? path : '/' + path}`;
  }

  function saveAuthUser(user) {
    localStorage.setItem('authUser', JSON.stringify(user));
  }

  function getAuthUser() {
    try {
      return JSON.parse(localStorage.getItem('authUser') || 'null');
    } catch (e) {
      return null;
    }
  }

  function clearAuthUser() {
    localStorage.removeItem('authUser');
  }

  function setMessage(element, text, isError = true) {
    if (!element) return;
    element.textContent = text || '';
    element.classList.remove('hidden');
    element.classList.toggle('text-error', !!isError);
    element.classList.toggle('text-primary', !isError);
  }

  async function apiFetch(path, options = {}) {
    const response = await fetch(buildUrl(path), {
      credentials: 'include',
      ...options,
      headers: {
        ...getAuthHeaders(options.body != null),
        ...(options.headers || {})
      }
    });

    const contentType = response.headers.get('content-type') || '';
    let data = null;

    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = text ? { message: text } : {};
    }

    if (!response.ok) {
      const message = data.error || data.message || `Ошибка ${response.status}`;
      throw new Error(message);
    }

    return data;
  }

  window.AuthAPI = {
    apiFetch,
    buildUrl,
    getCookie,
    getAuthHeaders,
    saveAuthUser,
    getAuthUser,
    clearAuthUser,
    setMessage
  };
})();