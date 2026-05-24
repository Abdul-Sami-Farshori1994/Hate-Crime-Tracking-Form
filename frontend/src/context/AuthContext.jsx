import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, persistLegacyToken } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [username, setUsername] = useState(null)
  const [role, setRole] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshSession = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/session')
      setUsername(data.username)
      setRole(data.role)
      if (data.access_token) {
        persistLegacyToken(data.access_token)
      }
      return data
    } catch {
      setUsername(null)
      setRole(null)
      persistLegacyToken(null)
      return null
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      await refreshSession()
      if (!cancelled) setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [refreshSession])

  const setToken = useCallback(
    async (token) => {
      if (token) {
        persistLegacyToken(token)
      } else {
        persistLegacyToken(null)
      }
      await refreshSession()
    },
    [refreshSession],
  )

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      /* ignore */
    }
    persistLegacyToken(null)
    setUsername(null)
    setRole(null)
  }, [])

  const value = useMemo(
    () => ({
      token: role ? 'cookie-session' : null,
      role,
      username,
      loading,
      setToken,
      logout,
      refreshSession,
    }),
    [role, username, loading, setToken, logout, refreshSession],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
