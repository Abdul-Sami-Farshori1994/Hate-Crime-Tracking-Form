import { AppShell, SurfaceCard } from '../components/forms-ui'

export default function NotFoundPage() {
  return (
    <AppShell width="narrow">
      <SurfaceCard className="mx-auto max-w-lg text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">404</p>
        <h1 className="mt-2 text-xl font-semibold text-slate-950">Page not found</h1>
        <p className="mt-3 text-sm text-slate-600">
          This address is not available. If you were given a shared link, check that you copied the full URL.
        </p>
      </SurfaceCard>
    </AppShell>
  )
}
