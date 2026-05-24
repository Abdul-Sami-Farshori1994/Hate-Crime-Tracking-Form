import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api'
import {
  FormLabel,
  PrimaryButton,
  StatusMessage,
  SurfaceCard,
  TextInput,
} from '../../components/forms-ui'
import PublicAccessUrls from '../../components/PublicAccessUrls'
import { useAuth } from '../../context/AuthContext'
import { adminLoginPath } from '../../paths'
import {
  PASSWORD_REQUIREMENTS_HINT,
  validatePasswordStrength,
} from '../../utils/passwordPolicy'

function usernameFromToken() {
  const token = localStorage.getItem('access_token')
  if (!token) return ''
  try {
    const [, payload] = token.split('.')
    if (!payload) return ''
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const json = JSON.parse(atob(normalized))
    return typeof json.sub === 'string' ? json.sub : ''
  } catch {
    return ''
  }
}

function validatePasswordPair(password, confirmPassword) {
  const newPassword = password.trim()
  const confirm = confirmPassword.trim()
  if (!newPassword && !confirm) return { ok: true, password: '' }
  if (!newPassword) return { ok: false, error: 'Enter a new password.' }
  const strength = validatePasswordStrength(newPassword)
  if (!strength.ok) return { ok: false, error: strength.error }
  if (newPassword !== confirm) return { ok: false, error: 'Passwords do not match.' }
  return { ok: true, password: newPassword }
}

function CredentialUpdateCard({
  title,
  apiPath,
  saveButtonLabel,
  usernamePlaceholder,
  passwordPlaceholder,
  loadErrorMessage,
  saveErrorMessage,
  successMessage,
}) {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  async function load() {
    try {
      const { data } = await api.get(apiPath)
      setUsername(data.username || '')
    } catch (err) {
      if (err?.response?.status === 404 && apiPath.includes('admin-access')) {
        const fallback = usernameFromToken()
        if (fallback) {
          setUsername(fallback)
          return
        }
      }
      throw err
    }
  }

  useEffect(() => {
    if (!token) {
      navigate(adminLoginPath(), { replace: true })
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        await load()
        if (!cancelled) setError(null)
      } catch (err) {
        if (!cancelled) {
          const detail = err?.response?.data?.detail
          if (err?.response?.status === 404 && apiPath.includes('admin-access')) {
            setError(
              typeof detail === 'string'
                ? detail
                : 'Admin credential API is unavailable. Restart the API: docker compose up -d --build api',
            )
          } else {
            setError(typeof detail === 'string' ? detail : loadErrorMessage)
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token, navigate, apiPath, loadErrorMessage])

  async function save(e) {
    e.preventDefault()
    setError(null)
    setMessage(null)

    const passwordCheck = validatePasswordPair(password, confirmPassword)
    if (!passwordCheck.ok) {
      setError(passwordCheck.error)
      return
    }

    if (
      passwordCheck.password &&
      !window.confirm('Update credentials? You will need the new password on next sign-in.')
    ) {
      return
    }

    setSaving(true)
    try {
      const payload = { username }
      if (passwordCheck.password) {
        payload.password = passwordCheck.password
      }
      await api.patch(apiPath, payload)
      setPassword('')
      setConfirmPassword('')
      setMessage(successMessage)
      await load()
    } catch (err) {
      const detail = err?.response?.data?.detail
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0]
        const msg =
          typeof first?.msg === 'string'
            ? first.msg
            : typeof first === 'string'
              ? first
              : saveErrorMessage
        setError(msg)
      } else {
        setError(typeof detail === 'string' ? detail : saveErrorMessage)
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <SurfaceCard className="max-w-xl">
      <h3 className="text-lg font-semibold text-slate-950">{title}</h3>

      {error && (
        <div className="mt-4">
          <StatusMessage>{error}</StatusMessage>
        </div>
      )}
      {message && (
        <div className="mt-4">
          <StatusMessage tone="success">{message}</StatusMessage>
        </div>
      )}

      <form onSubmit={save} className="mt-6 space-y-4">
        <FormLabel label="username">
          <TextInput
            placeholder={usernamePlaceholder}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={loading || saving}
          />
        </FormLabel>

        <FormLabel label="New password">
          <TextInput
            type="password"
            placeholder={passwordPlaceholder}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            autoComplete="new-password"
            disabled={loading || saving}
          />
          <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
            {PASSWORD_REQUIREMENTS_HINT}
          </p>
        </FormLabel>

        <FormLabel label="Confirm password">
          <TextInput
            type="password"
            placeholder="Re-enter the new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={loading || saving}
          />
        </FormLabel>

        <PrimaryButton type="submit" disabled={loading || saving}>
          {saving ? 'Saving…' : saveButtonLabel}
        </PrimaryButton>
      </form>
    </SurfaceCard>
  )
}

export default function CredentialManager() {
  const { token } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!token) {
      navigate(adminLoginPath(), { replace: true })
    }
  }, [token, navigate])

  return (
    <div className="space-y-6">
      <PublicAccessUrls />
      <div className="grid gap-6 xl:grid-cols-2">
        <CredentialUpdateCard
          title="Form Credential"
          apiPath="/admin/form-access"
          saveButtonLabel="Save form access"
          usernamePlaceholder="shared-form-user"
          passwordPlaceholder="Enter a new shared password"
          loadErrorMessage="Could not load form access settings."
          saveErrorMessage="Could not update form access."
          successMessage="Form credential updated successfully."
        />
        <CredentialUpdateCard
          title="Admin Credential"
          apiPath="/admin/admin-access"
          saveButtonLabel="Save admin access"
          usernamePlaceholder="admin"
          passwordPlaceholder="Enter a new admin password"
          loadErrorMessage="Could not load admin access settings."
          saveErrorMessage="Could not update admin access."
          successMessage="Admin credential updated successfully."
        />
      </div>
    </div>
  )
}
