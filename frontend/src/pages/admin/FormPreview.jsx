import { useEffect, useState } from 'react'
import { api } from '../../api'
import { EmptyState, Pill, SectionHeader, SurfaceCard } from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'

export default function FormPreview() {
  const { token } = useAuth()
  const [pages, setPages] = useState([])
  const [byPage, setByPage] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    ;(async () => {
      try {
        const { data: pgs } = await api.get('/form/pages')
        if (cancelled) return
        setPages(pgs)
        const qs = {}
        for (const p of pgs) {
          const { data } = await api.get(`/form/pages/${p.id}/questions`)
          qs[p.id] = data
        }
        if (!cancelled) setByPage(qs)
      } catch {
        if (!cancelled) setError('Could not load form preview.')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  if (error) {
    return (
      <SurfaceCard>
        <p className="text-sm text-rose-600">{error}</p>
      </SurfaceCard>
    )
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Preview"
        title="Read-only view of the live form"
        description="Use this page to review the same page titles and question structure respondents will see."
      />

      {pages.map((p) => (
        <SurfaceCard key={p.id} className="border-violet-200">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Pill tone="brand">Page {p.order_index + 1}</Pill>
              <Pill>{(byPage[p.id] || []).length} questions</Pill>
            </div>
            <div className="space-y-1">
              <h2 className="text-xl font-semibold text-slate-950">{p.title}</h2>
              {p.description && <p className="text-sm text-slate-600">{p.description}</p>}
            </div>
            <div className="grid gap-3">
              {(byPage[p.id] || []).map((q, index) => (
                <div key={q.id} className="rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Pill>Question {index + 1}</Pill>
                    <Pill tone={q.is_required ? 'success' : 'neutral'}>
                      {q.is_required ? 'Required' : 'Optional'}
                    </Pill>
                  </div>
                  <p className="mt-3 font-medium text-slate-900">{q.question_text}</p>
                  <p className="mt-1 text-sm text-slate-500">Answer type: {q.question_type}</p>
                </div>
              ))}
            </div>
          </div>
        </SurfaceCard>
      ))}
      {!pages.length && (
        <EmptyState
          title="No form pages yet"
          description="Create or seed pages and questions before using the preview workspace."
        />
      )}
    </div>
  )
}
