/** Unguessable URL path slugs (set at build time via Vite env). */

const SLUG_PATTERN = /^[A-Za-z0-9_-]{16,64}$/

const DEV_FORM_SLUG = 'Kp9mNx2vQw7Rt4yL8bHc1dF'
const DEV_ADMIN_SLUG = 'Hn3qWz8cRm6Tk5xP2vJk4mN'

function readSlug(raw, fallback) {
  const value = String(raw ?? '').trim()
  if (value && SLUG_PATTERN.test(value)) {
    return value
  }
  if (import.meta.env.PROD && value && !SLUG_PATTERN.test(value)) {
    console.warn('Path slug must be 16–64 URL-safe characters (A–Z, a–z, 0–9, _, -). Using fallback.')
  }
  return fallback
}

export const FORM_PATH_SLUG = readSlug(import.meta.env.VITE_FORM_PATH_SLUG, DEV_FORM_SLUG)
export const ADMIN_PATH_SLUG = readSlug(import.meta.env.VITE_ADMIN_PATH_SLUG, DEV_ADMIN_SLUG)

export const formPrefix = `/f/${FORM_PATH_SLUG}`
export const adminPrefix = `/a/${ADMIN_PATH_SLUG}`

export function formLoginPath() {
  return formPrefix
}

export function formPagePath() {
  return `${formPrefix}/form`
}

export function thankYouPath() {
  return `${formPrefix}/thank-you`
}

export function adminLoginPath() {
  return adminPrefix
}

export function adminDashboardPath(segment = '') {
  const base = `${adminPrefix}/dashboard`
  if (!segment) return base
  return `${base}/${String(segment).replace(/^\/+/, '')}`
}

export function isFormAppPath(pathname) {
  return pathname === formPrefix || pathname.startsWith(`${formPrefix}/`)
}

export function isAdminAppPath(pathname) {
  return pathname === adminPrefix || pathname.startsWith(`${adminPrefix}/`)
}

export function isLegacyPublicPath(pathname) {
  return (
    pathname === '/' ||
    pathname === '/form' ||
    pathname === '/thank-you' ||
    pathname === '/admin' ||
    pathname.startsWith('/admin/')
  )
}

export function publicAccessUrls(origin = typeof window !== 'undefined' ? window.location.origin : '') {
  const base = String(origin || '').replace(/\/+$/, '')
  return {
    formLogin: `${base}${formLoginPath()}`,
    form: `${base}${formPagePath()}`,
    adminLogin: `${base}${adminLoginPath()}`,
  }
}
