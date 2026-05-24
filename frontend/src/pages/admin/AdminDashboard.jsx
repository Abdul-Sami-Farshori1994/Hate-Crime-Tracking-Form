import { useEffect } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  AppShell,
  HeroCard,
  SecondaryButton,
  TabLink,
} from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'
import { adminDashboardPath, adminLoginPath, formLoginPath } from '../../paths'

const links = [
  { to: adminDashboardPath('preview'), label: 'Form preview', match: (p) => p.includes('/preview') },
  { to: adminDashboardPath('editor'), label: 'Form editor', match: (p) => p.includes('/editor') },
  { to: adminDashboardPath('responses'), label: 'Responses', match: (p) => p.includes('/responses') },
  { to: adminDashboardPath('analytics'), label: 'Analytics', match: (p) => p.includes('/analytics') },
  { to: adminDashboardPath('data-actions'), label: 'Data actions', match: (p) => p.includes('/data-actions') },
  { to: adminDashboardPath('credentials'), label: 'Form access', match: (p) => p.includes('/credentials') },
  { to: adminDashboardPath('audit'), label: 'Audit log', match: (p) => p.includes('/audit') },
]

export default function AdminDashboard() {
  const { token, role, logout, loading } = useAuth()
  const navigate = useNavigate()
  const path = useLocation().pathname

  useEffect(() => {
    if (loading) return
    if (!token) {
      navigate(adminLoginPath(), { replace: true })
      return
    }
    if (role && role !== 'admin') {
      logout().then(() => navigate(adminLoginPath(), { replace: true }))
    }
  }, [token, role, loading, logout, navigate])

  if (loading || !token || (role && role !== 'admin')) {
    return (
      <AppShell width="full">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">
          Loading…
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell width="full">
      <div className="space-y-6">
        <HeroCard
          centered
          showLogo
          logoSize="md"
          title="Hate Crime Tracking Form"
          subtitle="Admin Dashboard"
          subtitleClassName="tracking-wide"
          titleClassName="bg-gradient-to-r from-violet-700 via-violet-600 to-fuchsia-600 bg-clip-text text-transparent"
          action={
            <SecondaryButton
              onClick={() => {
                logout().then(() => navigate(adminLoginPath(), { replace: true }))
              }}
            >
              Log out
            </SecondaryButton>
          }
        />

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-slate-200 bg-white p-3 shadow-sm">
          <div className="-mx-1 flex min-w-0 flex-1 gap-2 overflow-x-auto px-1 pb-1">
            {links.map(({ to, label, match }) => (
              <TabLink key={to} to={to} active={match(path)}>
                {label}
              </TabLink>
            ))}
          </div>
          <Link to={formLoginPath()} className="px-2 text-sm font-medium text-violet-700 transition hover:text-violet-800">
            Open public form
          </Link>
        </div>

        <Outlet />
      </div>
    </AppShell>
  )
}
