/**
 * API Client with Keycloak Authentication
 */

const API_URL = import.meta.env.VITE_API_URL || '';

// Глобальный объект для хранения токена
let currentToken = null;

/**
 * Установить текущий JWT токен (вызывается из KeycloakContext)
 */
export const setAuthToken = (token) => {
  currentToken = token;
};

/**
 * Получить текущий JWT токен
 */
export const getAuthToken = () => currentToken;

/**
 * Get authorization header with Keycloak token
 */
const getAuthHeaders = () => {
  const token = getAuthToken();
  if (token) {
    return {
      'Authorization': `Bearer ${token}`,
    };
  }
  return {};
};

export async function apiRequest(path, options = {}) {
  const authHeaders = getAuthHeaders();
  
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep default message when the response is not JSON.
    }
    throw new Error(message);
  }

  return response.json();
}

// API для аутентификации (Keycloak)
// Эти функции должны вызываться из компонентов, где есть useKeycloak hook
export const authApi = {
  // Получить URL для входа с redirect (через OIDC callback)
  getLoginUrl: async (redirectAfter = null) => {
    const params = new URLSearchParams();
    if (redirectAfter) {
      params.append('redirect_after', redirectAfter);
    }
    
    const response = await fetch(`/api/oidc/login-url${params.toString() ? `?${params}` : ''}`);
    if (!response.ok) {
      throw new Error('Failed to get login URL');
    }
    return response.json();
  },
  
  // Вход через Keycloak (получает URL и делает redirect)
  // Должен вызываться из компонента с useKeycloak
  login: async (options = {}) => {
    const redirectAfter = options.redirectAfter || window.location.pathname;
    const loginData = await authApi.getLoginUrl(redirectAfter);
    
    // Делаем redirect на Keycloak
    window.location.href = loginData.login_url;
    return loginData;
  },
  
  // Выход из системы - должен вызываться из компонента с useKeycloak
  logout: (options = {}) => {
    // Этот метод должен быть переопределен в компоненте
    console.warn('authApi.logout() called without Keycloak context. Use useKeycloak().logout()');
    return Promise.resolve({});
  },
  
  // Получить текущего пользователя - должен вызываться из компонента с useKeycloak
  getCurrentUser: () => {
    console.warn('authApi.getCurrentUser() called without Keycloak context. Use useKeycloak().getToken()');
    return Promise.reject(new Error('Keycloak not available in this context'));
  },
};

// API для работы с вакансиями, кандидатами, откликами
export const hrApi = {
  dashboard: () => apiRequest('/api/dashboard'),
  vacancies: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const path = `/api/vacancies${queryString ? `?${queryString}` : ''}`;
    return apiRequest(path);
  },
  getVacancy: (id) => apiRequest(`/api/vacancies/${id}`),
  candidates: () => apiRequest('/api/candidates'),
  getCandidate: (id) => apiRequest(`/api/candidates/${id}`),
  applications: () => apiRequest('/api/applications'),
  seedDemo: () => apiRequest('/api/demo-seed', { method: 'POST' }),
  createVacancy: (payload) => apiRequest('/api/vacancies', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateVacancy: (id, payload) => apiRequest(`/api/vacancies/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deleteVacancy: (id) => apiRequest(`/api/vacancies/${id}`, {
    method: 'DELETE',
  }),
  closeVacancy: (id) => apiRequest(`/api/vacancies/${id}/close`, {
    method: 'PATCH',
  }),
  reopenVacancy: (id) => apiRequest(`/api/vacancies/${id}/reopen`, {
    method: 'PATCH',
  }),
  createCandidate: (payload) => apiRequest('/api/candidates', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateCandidate: (id, payload) => apiRequest(`/api/candidates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deleteCandidate: (id) => apiRequest(`/api/candidates/${id}`, {
    method: 'DELETE',
  }),
  createApplication: (payload) => apiRequest('/api/applications', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  analyzeApplication: (id) => apiRequest(`/api/applications/${id}/analyze`, { method: 'POST' }),
  interviewQuestions: (id) => apiRequest(`/api/applications/${id}/interview-questions`),
  updateApplicationStage: (id, stage) => apiRequest(`/api/applications/${id}/stage`, {
    method: 'PATCH',
    body: JSON.stringify({ stage }),
  }),
};

export const dashboardApi = {
  getDashboard: () => apiRequest('/api/dashboard'),
};

// API для работы с документами (база знаний)
export const documentsApi = {
  getDocuments: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const path = `/api/documents${queryString ? `?${queryString}` : ''}`;
    return apiRequest(path);
  },
  
  previewDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);

    return fetch(`${import.meta.env.VITE_API_URL || ''}/api/documents/preview`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    }).then(async (response) => {
      if (!response.ok) {
        let message = `Request failed: ${response.status}`;
        try {
          const body = await response.json();
          message = body.detail || message;
        } catch {
          // Keep default message when the response is not JSON.
        }
        throw new Error(message);
      }
      return response.json();
    });
  },

  uploadDocument: (formData) => {
    // Для загрузки файлов не используем JSON Content-Type
    return fetch(`${import.meta.env.VITE_API_URL || ''}/api/documents`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    }).then(async (response) => {
      if (!response.ok) {
        let message = `Request failed: ${response.status}`;
        try {
          const body = await response.json();
          message = body.detail || message;
        } catch {
          // Keep default message when the response is not JSON.
        }
        throw new Error(message);
      }
      return response.json();
    });
  },
  
  getDocument: (id) => apiRequest(`/api/documents/${id}`),

  getDocumentVersions: (id) => apiRequest(`/api/documents/${id}/versions`),

  getDocumentVersion: (id, versionNumber) => (
    apiRequest(`/api/documents/${id}/versions/${versionNumber}`)
  ),

  getDocumentFile: async (id, download = false) => {
    const response = await fetch(
      `${API_URL}/api/documents/${id}/file?download=${download}`,
      { headers: getAuthHeaders() }
    );
    if (!response.ok) {
      let message = `Request failed: ${response.status}`;
      try {
        const body = await response.json();
        message = body.detail || message;
      } catch {
        // Keep default message when the response is not JSON.
      }
      throw new Error(message);
    }
    return response.blob();
  },

  updateDocument: (id, payload) => apiRequest(`/api/documents/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),

  deleteDocument: (id) => apiRequest(`/api/documents/${id}`, { method: 'DELETE' }),

  restoreDocument: (id) => apiRequest(`/api/documents/${id}/restore`, { method: 'POST' }),
};

// API для уведомлений
export const notificationsApi = {
  getNotifications: (limit = 20, unreadOnly = false) => 
    apiRequest(`/api/notifications?limit=${limit}&unread_only=${unreadOnly}`),
  
  getUnreadCount: () => 
    apiRequest('/api/notifications/unread-count'),
  
  markAsRead: (notificationId) => 
    apiRequest(`/api/notifications/${notificationId}/read`, { method: 'POST' }),
  
  markAllAsRead: () => 
    apiRequest('/api/notifications/read-all', { method: 'POST' }),
  
  deleteNotification: (notificationId) => 
    apiRequest(`/api/notifications/${notificationId}`, { method: 'DELETE' }),
};
