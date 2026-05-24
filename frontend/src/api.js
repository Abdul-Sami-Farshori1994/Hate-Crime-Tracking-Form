import axios from 'axios'
import { adminLoginPath, formLoginPath, isAdminAppPath, isFormAppPath } from './paths'

const baseURL =
  (import.meta.env.VITE_API_BASE_URL && String(import.meta.env.VITE_API_BASE_URL).trim()) || ''

export const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

const AUTH_NO_REDIRECT_URLS = ['/auth/session', '/auth/login', '/auth/admin/login', '/auth/refresh', '/auth/logout']

function isAuthPublicRequest(url) {
  if (!url) return false
  return AUTH_NO_REDIRECT_URLS.some((part) => String(url).includes(part))
}

function isLoginPagePath(pathname) {
  return pathname === adminLoginPath() || pathname === formLoginPath()
}

function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)hc_csrf=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase()
  if (['post', 'put', 'patch', 'delete'].includes(method)) {
    const csrf = getCsrfToken()
    if (csrf) {
      config.headers['X-CSRF-Token'] = csrf
    }
  }
  const legacy = localStorage.getItem('access_token')
  if (legacy && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${legacy}`
  }
  return config
})

let refreshPromise = null

async function tryRefreshSession() {
  if (!refreshPromise) {
    refreshPromise = api
      .post('/auth/refresh')
      .then((r) => r.data)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (
      error?.response?.status === 401 &&
      original &&
      !original._retry &&
      !isAuthPublicRequest(original.url) &&
      !original.url?.includes('/auth/login') &&
      !original.url?.includes('/auth/admin/login') &&
      !original.url?.includes('/auth/refresh')
    ) {
      original._retry = true
      try {
        await tryRefreshSession()
        return api(original)
      } catch {
        /* fall through */
      }
    }

    if (error?.response?.status === 401 && original && !isAuthPublicRequest(original.url)) {
      localStorage.removeItem('access_token')
      const path = window.location.pathname
      if (isLoginPagePath(path)) {
        return Promise.reject(error)
      }
      if (isAdminAppPath(path)) {
        window.location.replace(adminLoginPath())
      } else if (isFormAppPath(path) && path !== formLoginPath()) {
        window.location.replace(formLoginPath())
      }
    }
    return Promise.reject(error)
  },
)

export function persistLegacyToken(token) {
  if (token) {
    localStorage.setItem('access_token', token)
  } else {
    localStorage.removeItem('access_token')
  }
}
