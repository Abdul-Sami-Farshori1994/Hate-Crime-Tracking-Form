const MIN_LENGTH = 8
const MAX_LENGTH = 128

const COMMON_PASSWORDS = new Set([
  'password',
  'password1',
  'password123',
  '12345678',
  '123456789',
  'qwerty123',
  'admin123',
  'letmein1',
  'welcome1',
  'changeme',
  'iloveyou',
])

export const PASSWORD_REQUIREMENTS_HINT =
  'At least 8 characters with uppercase, lowercase, a number, and a symbol (e.g. ! @ # $).'

const COMPLEXITY_ERROR =
  'Password must be at least 8 characters and include uppercase, lowercase, a number, and a symbol (e.g. ! @ # $).'

export function validatePasswordStrength(password) {
  if (!password) {
    return { ok: false, error: 'Enter a new password.' }
  }
  if (password.length < MIN_LENGTH || password.length > MAX_LENGTH) {
    return { ok: false, error: COMPLEXITY_ERROR }
  }
  if (!/[A-Z]/.test(password)) {
    return { ok: false, error: COMPLEXITY_ERROR }
  }
  if (!/[a-z]/.test(password)) {
    return { ok: false, error: COMPLEXITY_ERROR }
  }
  if (!/\d/.test(password)) {
    return { ok: false, error: COMPLEXITY_ERROR }
  }
  if (!/[^A-Za-z0-9]/.test(password)) {
    return { ok: false, error: COMPLEXITY_ERROR }
  }

  const normalized = password.trim().toLowerCase()
  if (COMMON_PASSWORDS.has(normalized)) {
    return {
      ok: false,
      error: 'Password is too common. Choose a stronger, unique password.',
    }
  }

  if (new Set(password).size < 5) {
    return {
      ok: false,
      error: 'Password is too simple. Use a mix of varied characters.',
    }
  }

  return { ok: true }
}
