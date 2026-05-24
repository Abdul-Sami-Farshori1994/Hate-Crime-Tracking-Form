import { useMemo, useState } from 'react'
import { publicAccessUrls } from '../paths'
import { SecondaryButton, SurfaceCard } from './forms-ui'

function CopyField({ label, url }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <code className="block min-w-0 flex-1 break-all rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-800">
          {url}
        </code>
        <SecondaryButton type="button" className="shrink-0" onClick={copy}>
          {copied ? 'Copied' : 'Copy'}
        </SecondaryButton>
      </div>
    </div>
  )
}

export default function PublicAccessUrls() {
  const urls = useMemo(() => publicAccessUrls(), [])

  return (
    <SurfaceCard className="xl:col-span-2">
      <h3 className="text-base font-semibold text-slate-950">Shared entry links</h3>
      <p className="mt-1 text-sm text-slate-600">
        Only people with these exact URLs can reach the sign-in pages. Passwords and MFA are still required after
        opening a link.
      </p>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <CopyField label="Form sign-in (share with respondents)" url={urls.formLogin} />
        <CopyField label="Admin sign-in (share with staff)" url={urls.adminLogin} />
      </div>
    </SurfaceCard>
  )
}
