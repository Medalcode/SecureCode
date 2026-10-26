const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const TOKEN_KEY = 'securecode_token';
export const USER_KEY = 'securecode_user';

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token, username) {
  localStorage.setItem(TOKEN_KEY, token);
  if (username) {
    localStorage.setItem(USER_KEY, username);
  }
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser() {
  return localStorage.getItem(USER_KEY) || 'Auditor';
}

export function isAuthenticated() {
  return Boolean(getStoredToken());
}

/**
 * Autenticación contra POST /api/v1/auth/token (OAuth2 Bearer x-www-form-urlencoded)
 */
export async function loginUser(username, password) {
  try {
    const params = new URLSearchParams();
    params.append('username', username.trim());
    params.append('password', password);

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
      },
      body: params.toString(),
    });

    if (response.status === 401) {
      return {
        success: false,
        status: 401,
        message: 'Credenciales inválidas. Verifique su usuario y contraseña.',
      };
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        status: response.status,
        message: errorData.detail || `Error en el servidor de autenticación (HTTP ${response.status}).`,
      };
    }

    const data = await response.json();
    setStoredToken(data.access_token, username.trim());

    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      status: 0,
      message: 'No fue posible conectar con el backend de SecureCode (FastAPI). Verifique que el servicio esté activo.',
    };
  }
}

