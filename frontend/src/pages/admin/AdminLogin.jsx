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

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { data } = await api.post('/auth/admin/login', { username, password })
      if (data?.access_token) {
        persistLegacyToken(data.access_token)
      }
      await refreshSession()
      navigate(adminDashboardPath())
    } catch (err) {
      setError(`Login failed: ${formatError(err)}`)
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
          <form onSubmit={onSubmit} className="space-y-4">
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
              {loading ? 'Signing in…' : 'Sign in'}
            </PrimaryButton>
          </form>
        </HeroCard>
      </div>
    </AppShell>
  )
}
