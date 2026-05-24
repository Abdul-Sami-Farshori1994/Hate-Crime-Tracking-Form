import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api'
import {
  EmptyState,
  FormLabel,
  Pill,
  PrimaryButton,
  SecondaryButton,
  SectionHeader,
  StatCard,
  SurfaceCard,
  TextInput,
} from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'
import { adminDashboardPath, adminLoginPath } from '../../paths'

const PAGE_SIZE = 15

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

function getApiMessage(err, fallback) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  return fallback
}

/** Supports paginated API `{ items, total_count, next_cursor }` and legacy array responses. */
function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    const items = data.map((row) => ({
      session_id: row.session_id,
      respondent_name: row.respondent_name ?? null,
      submitted_at: row.submitted_at,
      answer_count: row.answer_count ?? (row.answers || []).length,
    }))
    return {
      items,
      next_cursor: null,
      total_count: items.length,
    }
  }
  return {
    items: data?.items || [],
    next_cursor: data?.next_cursor ?? null,
    total_count: data?.total_count ?? data?.items?.length ?? 0,
  }
}

export default function Responses() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [nextCursor, setNextCursor] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    const timer = setTimeout(() => setSearchQuery(search.trim()), 350)
    return () => clearTimeout(timer)
  }, [search])

  const loadPage = useCallback(
    async (cursor, append, query) => {
      const params = { limit: PAGE_SIZE }
      if (cursor) params.cursor = cursor
      if (query) params.q = query

      const { data } = await api.get('/responses/', { params })
      const page = normalizeListResponse(data)
      setTotalCount(page.total_count)
      setNextCursor(page.next_cursor)
      setRows((prev) => (append ? [...prev, ...page.items] : page.items))
    },
    [],
  )

  useEffect(() => {
    if (!token) {
      navigate(adminLoginPath(), { replace: true })
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        await loadPage(null, false, searchQuery)
      } catch (err) {
        if (!cancelled) setError(getApiMessage(err, 'Could not load responses.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token, navigate, loadPage, searchQuery])

  async function handleLoadMore() {
    if (!nextCursor || loadingMore) return
    setLoadingMore(true)
    setError(null)
    try {
      await loadPage(nextCursor, true, searchQuery)
    } catch (err) {
      setError(getApiMessage(err, 'Could not load more responses.'))
    } finally {
      setLoadingMore(false)
    }
  }

  async function handleDelete(row) {
    const label = row.respondent_name || row.session_id
    const confirmed = window.confirm(
      `Delete this response?\n\n${label}\n\nIt will be removed from the list and analytics. The respondent can submit again with the same name. This cannot be undone from the admin UI.`,
    )
    if (!confirmed) return

    setDeletingId(row.session_id)
    setError(null)
    try {
      await api.delete(`/responses/${encodeURIComponent(row.session_id)}`)
      setRows((prev) => prev.filter((r) => r.session_id !== row.session_id))
      setTotalCount((count) => Math.max(0, count - 1))
    } catch (err) {
      setError(getApiMessage(err, 'Could not delete this response.'))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Responses"
        title="Review submitted reports"
        description="Browse all submissions in a compact list. Open any response to read the full answers."
      />

      <StatCard
        label="Total responses"
        value={loading ? '—' : totalCount}
        help="All submission sessions stored in the system"
        tone="brand"
      />

      {error && (
        <SurfaceCard>
          <p className="text-sm text-rose-600">{error}</p>
        </SurfaceCard>
      )}

      <SurfaceCard className="overflow-hidden p-0">
        <div className="border-b border-slate-200 px-5 py-4 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-950">All responses</h3>
              <p className="mt-1 text-sm text-slate-600">
                Newest first · {rows.length} of {totalCount} shown
              </p>
            </div>
            <FormLabel label="Search by name" className="w-full sm:max-w-xs">
              <TextInput
                type="search"
                placeholder="Respondent name…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Search responses by respondent name"
              />
            </FormLabel>
          </div>
        </div>

        {loading && (
          <p className="px-5 py-8 text-sm text-slate-600 sm:px-6">Loading responses…</p>
        )}

        {!loading && rows.length > 0 && (
          <ul className="divide-y divide-slate-200">
            {rows.map((r, index) => (
              <li
                key={r.session_id}
                className="flex flex-wrap items-center justify-between gap-4 px-5 py-4 transition hover:bg-violet-50/40 sm:px-6"
              >
                <div className="min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Pill tone="brand">#{index + 1}</Pill>
                    <Pill tone={r.respondent_name ? 'success' : 'neutral'}>
                      {r.respondent_name || 'Unnamed submission'}
                    </Pill>
                    <span className="text-sm text-slate-500">{formatDate(r.submitted_at)}</span>
                  </div>
                  <p className="text-sm text-slate-500">
                    {r.answer_count} answer{r.answer_count === 1 ? '' : 's'}
                  </p>
                  <p className="truncate font-mono text-xs text-slate-400">{r.session_id}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Link
                    to={adminDashboardPath(`responses/${r.session_id}`)}
                    className="inline-flex items-center justify-center rounded-2xl border border-violet-200 bg-violet-50 px-4 py-2.5 text-sm font-semibold text-violet-800 transition hover:border-violet-300 hover:bg-violet-100"
                  >
                    View
                  </Link>
                  <SecondaryButton
                    type="button"
                    disabled={deletingId === r.session_id}
                    onClick={() => handleDelete(r)}
                    className="border-rose-200 text-rose-700 hover:border-rose-300 hover:bg-rose-50"
                  >
                    {deletingId === r.session_id ? 'Deleting…' : 'Delete'}
                  </SecondaryButton>
                </div>
              </li>
            ))}
          </ul>
        )}

        {!loading && !rows.length && !error && (
          <div className="p-6">
            <EmptyState
              title="No submissions yet"
              description="Once respondents submit the form, their responses will appear in this list."
            />
          </div>
        )}

        {!loading && nextCursor && (
          <div className="border-t border-slate-200 px-5 py-4 text-center sm:px-6">
            <PrimaryButton type="button" onClick={handleLoadMore} disabled={loadingMore}>
              {loadingMore ? 'Loading…' : 'Load more'}
            </PrimaryButton>
          </div>
        )}
      </SurfaceCard>
    </div>
  )
}
