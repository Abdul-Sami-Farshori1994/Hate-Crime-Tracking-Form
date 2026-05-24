import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, persistLegacyToken } from '../../api'
import { AppShell, FormLabel, HeroCard, PrimaryButton, StatusMessage, TextInput } from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'
import { adminDashboardPath } from '../../paths'

export default function AdminLogin() {
  const { refreshSession } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [step, setStep] = useState('password')
  const [provisioningUri, setProvisioningUri] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  function formatError(err) {
    const data = err?.response?.data
    const detail = typeof data === 'string' ? data : data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d.msg || d).join(' ')
    if (err?.response?.status) {
      return `HTTP ${err.response.status} — check API logs and database.`
    }
    return err?.message || 'Network error — is the API running?'
  }

  async function finishSession(data) {
    if (data?.access_token) {
      persistLegacyToken(data.access_token)
    }
    await refreshSession()
    navigate(adminDashboardPath())
  }

  async function onPasswordSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { data } = await api.post('/auth/admin/login', { username, password })
      if (data.mfa_setup_required) {
        setProvisioningUri(data.provisioning_uri || null)
        setStep('mfa_setup')
        return
      }
      if (data.mfa_required) {
        setStep('mfa')
        return
      }
      await finishSession(data)
    } catch (err) {
      setError(`Login failed: ${formatError(err)}`)
    } finally {
      setLoading(false)
    }
  }

  async function onMfaSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const path = step === 'mfa_setup' ? '/auth/admin/mfa/confirm' : '/auth/admin/mfa/verify'
    try {
      const { data } = await api.post(path, { code: mfaCode.replace(/\s/g, '') })
      await finishSession(data)
    } catch (err) {
      setError(`Verification failed: ${formatError(err)}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell width="narrow">
      <div className="mx-auto flex min-h-[78vh] max-w-xl items-center justify-center">
        <HeroCard
          className="w-full"
          showLogo
          logoSize="lg"
          centered
          title={
            <>
              <span>Hate Crime Tracking</span>
              <span className="mt-4 block text-base font-normal text-slate-500 sm:text-lg">
                Admin Dashboard
              </span>
            </>
          }
        >
          {step === 'password' && (
            <form onSubmit={onPasswordSubmit} className="space-y-4">
              <FormLabel label="Username">
                <TextInput
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="Enter username"
                />
              </FormLabel>

              <FormLabel label="Password">
                <TextInput
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="Enter password"
                />
              </FormLabel>

              {error && <StatusMessage>{error}</StatusMessage>}

              <PrimaryButton type="submit" tone="dark" disabled={loading} className="w-full">
                {loading ? 'Signing in…' : 'Continue'}
              </PrimaryButton>
            </form>
          )}

          {(step === 'mfa' || step === 'mfa_setup') && (
            <form onSubmit={onMfaSubmit} className="space-y-4">
              <p className="text-sm text-slate-600">
                {step === 'mfa_setup'
                  ? 'Set up two-factor authentication. Add this account to your authenticator app, then enter the 6-digit code.'
                  : 'Enter the 6-digit code from your authenticator app.'}
              </p>
              {provisioningUri && (
                <p className="break-all rounded-lg bg-slate-100 p-3 text-xs text-slate-700">
                  {provisioningUri}
                </p>
              )}
              <FormLabel label="Authentication code">
                <TextInput
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  required
                  placeholder="000000"
                />
              </FormLabel>
              {error && <StatusMessage>{error}</StatusMessage>}
              <PrimaryButton type="submit" tone="dark" disabled={loading} className="w-full">
                {loading ? 'Verifying…' : 'Verify and sign in'}
              </PrimaryButton>
            </form>
          )}
        </HeroCard>
      </div>
    </AppShell>
  )
}
