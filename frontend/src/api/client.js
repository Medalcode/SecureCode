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

/**
 * Ejecutar evaluación de control (GH-001 o GH-002)
 */
export async function evaluateControl(controlId, payload) {
  const token = getStoredToken();
  const endpoint = controlId === 'GH-002'
    ? `${API_BASE_URL}/api/v1/evaluations/gh-002`
    : `${API_BASE_URL}/api/v1/evaluations/gh-001`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });

    if (response.status === 401) {
      clearSession();
      return {
        success: false,
        status: 401,
        message: 'Sesión expirada o no autorizada. Por favor inicie sesión nuevamente.',
      };
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        status: response.status,
        message: typeof errorData.detail === 'string' ? errorData.detail : `Error en la evaluación (HTTP ${response.status}).`,
      };
    }

    const data = await response.json();
    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      status: 0,
      message: 'Falla de infraestructura de red o servicio no disponible. Reintentar más tarde.',
    };
  }
}

/**
 * Obtener historial de evaluaciones registradas en PostgreSQL
 */
export async function fetchEvaluationsHistory({ status = null, search = '', limit = 50, offset = 0 } = {}) {
  const token = getStoredToken();
  const params = new URLSearchParams();
  if (status && status !== 'Todos') {
    params.append('status', status);
  }
  if (search && search.trim()) {
    params.append('search', search.trim());
  }
  if (limit) params.append('limit', limit);
  if (offset) params.append('offset', offset);

  const queryStr = params.toString() ? `?${params.toString()}` : '';
  const endpoint = `${API_BASE_URL}/api/v1/evaluations${queryStr}`;

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });

    if (response.status === 401) {
      clearSession();
      return {
        success: false,
        status: 401,
        message: 'Sesión expirada o no autorizada. Por favor inicie sesión nuevamente.',
      };
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        status: response.status,
        message: typeof errorData.detail === 'string' ? errorData.detail : `Error al cargar historial (HTTP ${response.status}).`,
      };
    }

    const data = await response.json();
    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      status: 0,
      message: 'No fue posible conectar con el servidor para obtener el historial.',
    };
  }
}

/**
 * Obtener métricas y estado del Centro de Control y Facturación
 */
export async function fetchBillingSummary() {
  const token = getStoredToken();
  const endpoint = `${API_BASE_URL}/api/v1/billing/summary`;

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });

    if (response.status === 401) {
      clearSession();
      return {
        success: false,
        status: 401,
        message: 'Sesión expirada o no autorizada. Por favor inicie sesión nuevamente.',
      };
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        status: response.status,
        message: typeof errorData.detail === 'string' ? errorData.detail : `Error al cargar métricas de facturación (HTTP ${response.status}).`,
      };
    }

    const data = await response.json();
    return {
      success: true,
      data,
    };
  } catch (err) {
    return {
      success: false,
      status: 0,
      message: 'No fue posible conectar con el endpoint de facturación.',
    };
  }
}
