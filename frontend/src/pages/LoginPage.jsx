import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, persistLegacyToken } from '../api'
import { AppShell, FormLabel, HeroCard, PrimaryButton, StatusMessage, TextInput } from '../components/forms-ui'
import { useAuth } from '../context/AuthContext'
import { formPagePath } from '../paths'

export default function LoginPage() {
  const { refreshSession } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { username, password })
      if (data.access_token) {
        persistLegacyToken(data.access_token)
      }
      await refreshSession()
      navigate(formPagePath())
    } catch (err) {
      const data = err?.response?.data
      const detail = typeof data === 'string' ? data : data?.detail
      const msg =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || d).join(' ')
            : err?.response?.status
              ? `HTTP ${err.response.status} — check API logs and database (DATABASE_URL / Postgres running).`
              : err?.message || 'Network error — is the API running on port 8000?'
      setError(`Login failed: ${msg}`)
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
          title="Hate Crime Tracking"
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

            <div className="flex flex-col gap-3 pt-2">
              <PrimaryButton type="submit" disabled={loading} className="w-full">
                {loading ? 'Signing in…' : 'Continue to form'}
              </PrimaryButton>
            </div>
          </form>
        </HeroCard>
      </div>
    </AppShell>
  )
}
