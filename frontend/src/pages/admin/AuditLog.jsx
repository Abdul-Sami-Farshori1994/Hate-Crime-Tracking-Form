import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api'
import {
  EmptyState,
  Pill,
  PrimaryButton,
  SectionHeader,
  StatusMessage,
  SurfaceCard,
} from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'
import { adminLoginPath } from '../../paths'

const ACTION_LABELS = {
  create_form_page: 'Create section',
  update_form_page: 'Update section',
  delete_form_page: 'Hide section',
  restore_form_page: 'Unhide section',
  create_question: 'Create question',
  update_question: 'Update question',
  delete_question: 'Hide question',
  restore_question: 'Unhide question',
  reorder_questions: 'Reorder questions',
  sync_global_order: 'Sync form order',
  replace_branch_rules: 'Update branching',
  update_form_access: 'Update form login',
  update_admin_access: 'Update admin login',
  export_responses: 'Export responses',
  soft_delete_response: 'Delete response',
  login_success: 'Login succeeded',
  login_failed: 'Login failed',
  admin_login_new_ip: 'Admin login (new IP)',
  submit_response: 'Form submitted',
}

function formatWhen(value) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatDetail(detail) {
  if (detail == null) return '—'
  if (typeof detail === 'string') return detail
  try {
    const text = JSON.stringify(detail)
    return text.length > 120 ? `${text.slice(0, 120)}…` : text
  } catch {
    return '—'
  }
}

export default function AuditLog() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get('/admin/audit-events', { params: { limit: 100 } })
      setRows(Array.isArray(data) ? data : [])
    } catch (err) {
      setRows([])
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Could not load audit log. Run database migration (alembic upgrade head).',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!token) {
      navigate(adminLoginPath(), { replace: true })
      return
    }
    load()
  }, [token, navigate, load])

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Security"
        title="Audit log"
        description="Recent admin and security-sensitive actions (last 100 events)."
        action={
          <PrimaryButton type="button" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </PrimaryButton>
        }
      />

      {error && <StatusMessage>{error}</StatusMessage>}

      <SurfaceCard className="overflow-hidden p-0">
        {loading && !rows.length ? (
          <p className="p-6 text-sm text-slate-600">Loading audit events…</p>
        ) : !rows.length ? (
          <div className="m-6">
            <EmptyState
              title="No audit events yet"
              description="Actions such as form edits, credential changes, exports, and deletions appear here."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">When</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Resource</th>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">IP</th>
                  <th className="px-4 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => (
                  <tr key={row.id} className="hover:bg-violet-50/40">
                    <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                      {formatWhen(row.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <Pill tone="brand">{ACTION_LABELS[row.action] || row.action}</Pill>
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      <span className="font-medium">{row.resource_type}</span>
                      {row.resource_id ? (
                        <span className="text-slate-500"> / {row.resource_id}</span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {row.user_id != null ? `#${row.user_id}` : '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">
                      {row.ip_address || '—'}
                    </td>
                    <td className="max-w-xs px-4 py-3 font-mono text-xs text-slate-500">
                      {formatDetail(row.detail)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SurfaceCard>
    </div>
  )
}
