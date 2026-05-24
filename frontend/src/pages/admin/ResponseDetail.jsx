import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api'
import { Pill, SectionHeader, SecondaryButton, SurfaceCard } from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'
import { adminDashboardPath, adminLoginPath } from '../../paths'

function formatDate(value) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatChoiceLabel(item) {
  const s = String(item)
  if (s.startsWith('Other: ')) {
    const detail = s.slice('Other: '.length).trim()
    return detail ? `Other — ${detail}` : 'Other'
  }
  return s
}

function formatAnswer(questionType, raw) {
  if (!raw) return 'No answer'
  if (questionType === 'checkbox') {
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed.map(formatChoiceLabel).join(', ')
    } catch {
      return raw
    }
  }
  if (typeof raw === 'string' && raw.startsWith('Other: ')) {
    return formatChoiceLabel(raw)
  }
  return raw
}

function getApiMessage(err, fallback) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (err?.response?.status === 404) {
    return 'Response not found. Rebuild the API container: docker compose up -d --build api'
  }
  return fallback
}

async function fetchResponseDetail(sessionId) {
  try {
    const { data } = await api.get(`/responses/${encodeURIComponent(sessionId)}`)
    return data
  } catch (err) {
    if (err?.response?.status !== 404) throw err
    const { data: listData } = await api.get('/responses/', { params: { limit: 200 } })
    if (Array.isArray(listData)) {
      const row = listData.find((item) => String(item.session_id) === String(sessionId))
      if (row) return row
    }
    const items = listData?.items
    if (Array.isArray(items)) {
      const row = items.find((item) => String(item.session_id) === String(sessionId))
      if (row && row.answers) return row
    }
    throw err
  }
}

export default function ResponseDetail() {
  const { sessionId } = useParams()
  const { token } = useAuth()
  const navigate = useNavigate()
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!token) {
      navigate(adminLoginPath(), { replace: true })
      return
    }
    if (!sessionId) return

    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await fetchResponseDetail(sessionId)
        if (!cancelled) setDetail(data)
      } catch (err) {
        if (!cancelled) setError(getApiMessage(err, 'Could not load this response.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [token, sessionId, navigate])

  async function handleDelete() {
    if (!sessionId || !detail) return
    const label = detail.respondent_name || sessionId
    const confirmed = window.confirm(
      `Delete this response?\n\n${label}\n\nIt will be removed from the list and analytics. The respondent can submit again with the same name.`,
    )
    if (!confirmed) return

    setDeleting(true)
    setError(null)
    try {
      await api.delete(`/responses/${encodeURIComponent(sessionId)}`)
      navigate(adminDashboardPath('responses'), { replace: true })
    } catch (err) {
      setError(getApiMessage(err, 'Could not delete this response.'))
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">Response details</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">
            {detail?.respondent_name || 'Submission review'}
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to={adminDashboardPath('responses')}
            className="inline-flex items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:border-violet-200 hover:bg-violet-50/60"
          >
            Back to all responses
          </Link>
          {detail && !loading && (
            <SecondaryButton
              type="button"
              disabled={deleting}
              onClick={handleDelete}
              className="border-rose-200 text-rose-700 hover:border-rose-300 hover:bg-rose-50"
            >
              {deleting ? 'Deleting…' : 'Delete response'}
            </SecondaryButton>
          )}
        </div>
      </div>

      {loading && (
        <SurfaceCard>
          <p className="text-sm text-slate-600">Loading response…</p>
        </SurfaceCard>
      )}

      {error && (
        <SurfaceCard>
          <p className="text-sm text-rose-600">{error}</p>
          <SecondaryButton type="button" className="mt-4" onClick={() => navigate(adminDashboardPath('responses'))}>
            Back to all responses
          </SecondaryButton>
        </SurfaceCard>
      )}

      {detail && !loading && (
        <>
          <SurfaceCard>
            <SectionHeader
              eyebrow="Respondent"
              title={detail.respondent_name || 'Unnamed respondent'}
              description={`Submitted on ${formatDate(detail.submitted_at)}`}
            />
            <p className="mt-4 font-mono text-xs text-slate-400">{detail.session_id}</p>
          </SurfaceCard>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-950">Answers</h3>
            {(detail.answers || []).map((a, index) => (
              <SurfaceCard key={`${detail.session_id}-${a.question_id}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <Pill tone="brand">Question {index + 1}</Pill>
                  <Pill>{a.question_type}</Pill>
                </div>
                <p className="mt-4 text-base font-semibold text-slate-950">{a.question_text}</p>
                <p className="mt-4 rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-7 text-slate-800">
                  {formatAnswer(a.question_type, a.answer_value)}
                </p>
              </SurfaceCard>
            ))}

            {!detail.answers?.length && (
              <SurfaceCard>
                <p className="text-sm text-slate-600">No answers were recorded for this session.</p>
              </SurfaceCard>
            )}
          </div>
        </>
      )}
    </div>
  )
}
