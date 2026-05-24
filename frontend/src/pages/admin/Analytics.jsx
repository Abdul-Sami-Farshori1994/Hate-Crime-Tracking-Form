import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../../api'
import { EmptyState, SectionHeader, SurfaceCard } from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'
import { adminLoginPath } from '../../paths'

const CHART_COLORS = [
  '#3b82f6',
  '#f97316',
  '#22c55e',
  '#ef4444',
  '#a855f7',
  '#a16207',
  '#ec4899',
  '#94a3b8',
]

const PIE_CHART_MAX_OPTIONS = 5

function isLegacySummaryBar(breakdown) {
  return breakdown.length === 1 && breakdown[0]?.label === 'responses'
}

function inferChartType(questionType, breakdown) {
  if (questionType === 'text' || questionType === 'date') return 'summary'
  if (isLegacySummaryBar(breakdown)) return 'summary'
  if (questionType === 'checkbox' || questionType === 'rating') return 'bar'
  if (questionType === 'radio' || questionType === 'select') {
    return breakdown.length <= PIE_CHART_MAX_OPTIONS ? 'pie' : 'bar'
  }
  if (breakdown.length <= PIE_CHART_MAX_OPTIONS) return 'pie'
  return 'bar'
}

function inferQuestionType(breakdown) {
  if (isLegacySummaryBar(breakdown)) return 'text'
  return 'choice'
}

/** Supports new analytics API and legacy `{ bars }` responses. */
function normalizeAnalyticsQuestion(raw, index) {
  const breakdown = raw.breakdown ?? raw.bars ?? []
  const questionType = raw.question_type ?? inferQuestionType(breakdown)
  const chartType = raw.chart_type ?? inferChartType(questionType, breakdown)
  const totalResponses =
    raw.total_responses ??
    (isLegacySummaryBar(breakdown)
      ? Number(breakdown[0]?.count ?? 0)
      : breakdown.reduce((sum, row) => sum + Number(row?.count ?? 0), 0))

  return {
    question_id: raw.question_id,
    question_text: raw.question_text ?? 'Question',
    question_type: questionType,
    question_number: raw.question_number ?? index + 1,
    chart_type: chartType,
    total_responses: totalResponses,
    breakdown: chartType === 'summary' ? [] : breakdown,
    latest_responses: raw.latest_responses ?? [],
  }
}

function normalizeAnalyticsResponse(data) {
  if (!data) return { questions: [], total_sessions: 0 }
  const questions = (data.questions || []).map(normalizeAnalyticsQuestion)
  return {
    total_sessions: data.total_sessions ?? 0,
    questions,
  }
}

function truncateLabel(label, max = 36) {
  const s = String(label)
  return s.length > max ? `${s.slice(0, max)}…` : s
}

function ChoiceLegend({ breakdown, centered = false, compact = false }) {
  if (!breakdown?.length) {
    return <p className={`text-sm text-slate-500 ${centered ? 'text-center' : ''}`}>No responses yet.</p>
  }
  return (
    <ul
      className={
        centered
          ? compact
            ? 'mx-auto flex max-h-40 max-w-4xl flex-wrap justify-center gap-x-6 gap-y-2 overflow-y-auto pr-1'
            : 'mx-auto flex max-w-2xl flex-wrap justify-center gap-x-8 gap-y-3'
          : 'grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-1 sm:gap-y-3'
      }
    >
      {breakdown.map((row, index) => (
        <li key={`${row.label}-${index}`} className="flex min-w-0 items-start gap-2.5">
          <span
            className="mt-1.5 h-3 w-3 shrink-0 rounded-full"
            style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
          />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-slate-800" title={row.label}>
              {truncateLabel(row.label, 28)}
            </p>
            <p className="text-base font-semibold tabular-nums text-slate-950 sm:text-lg">{row.count}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}

function ChartFrame({ children, className = '', centered = false, style = {} }) {
  return (
    <div
      className={`relative min-w-0 overflow-hidden ${centered ? 'mx-auto' : 'w-full'} ${className}`}
      style={{
        minHeight: 200,
        height: 'clamp(200px, 42vw, 380px)',
        width: centered ? undefined : '100%',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

function useNarrowViewport() {
  const [narrow, setNarrow] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia('(max-width: 639px)').matches : false,
  )
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 639px)')
    const onChange = () => setNarrow(mq.matches)
    onChange()
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return narrow
}

function TextSummaryPanel({ total, latest }) {
  return (
    <div className="mx-auto grid w-full max-w-4xl gap-6 sm:grid-cols-[1fr_minmax(0,280px)]">
      <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-100 bg-slate-50/60 px-4 py-8 sm:px-6 sm:py-10">
        <p className="text-4xl font-bold tabular-nums text-slate-950 sm:text-5xl">{total}</p>
        <p className="mt-2 text-sm font-medium text-slate-600">Responses</p>
      </div>
      <div className="rounded-2xl border border-slate-100 bg-white px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Latest responses</p>
        {latest?.length ? (
          <ul className="mt-3 space-y-2">
            {latest.map((sample, i) => (
              <li key={`${sample}-${i}`} className="text-sm italic text-slate-700">
                &ldquo;{truncateLabel(sample, 48)}&rdquo;
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-slate-500">No responses yet.</p>
        )}
      </div>
    </div>
  )
}

function ChoiceChartPanel({ chartType, breakdown, centered = false }) {
  const narrow = useNarrowViewport()
  const data = useMemo(
    () =>
      (breakdown || []).map((row, index) => ({
        ...row,
        fill: CHART_COLORS[index % CHART_COLORS.length],
      })),
    [breakdown],
  )
  if (!data.length) {
    return (
      <div className="flex min-h-[200px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/50">
        <p className="text-sm text-slate-500">No chart data yet.</p>
      </div>
    )
  }

  if (chartType === 'pie') {
    const pieChart = (
      <ChartFrame
        centered={centered}
        style={centered ? { width: 'min(100%, 420px)', maxWidth: '100%' } : undefined}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="label"
              cx="50%"
              cy="50%"
              innerRadius="0%"
              outerRadius="78%"
              paddingAngle={2}
              stroke="#fff"
              strokeWidth={2}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [value, 'Count']}
              labelFormatter={(label) => truncateLabel(label, 60)}
            />
          </PieChart>
        </ResponsiveContainer>
      </ChartFrame>
    )

    if (centered) {
      return <div className="flex w-full justify-center">{pieChart}</div>
    }

    return pieChart
  }

  const manyOptions = data.length > 8
  const labelAngle = manyOptions ? -55 : narrow ? -45 : -32
  const bottomMargin = manyOptions ? 96 : narrow ? 56 : 72
  const barSlotWidth = centered
    ? Math.min(manyOptions ? 960 : 768, Math.max(360, data.length * (manyOptions ? 48 : 72) + 120))
    : null

  const barChart = (
    <ChartFrame
      centered={centered}
      className={manyOptions ? 'min-h-[280px]' : ''}
      style={centered && barSlotWidth ? { width: barSlotWidth, maxWidth: '100%' } : undefined}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{
            top: 8,
            right: centered ? 32 : 8,
            left: centered ? 32 : 0,
            bottom: bottomMargin,
          }}
        >
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: narrow ? 9 : 10, fill: '#64748b' }}
            interval={0}
            angle={labelAngle}
            textAnchor="end"
            height={bottomMargin - 8}
            tickFormatter={(v) => truncateLabel(v, manyOptions ? 12 : narrow ? 10 : 14)}
          />
          <YAxis allowDecimals={false} tick={{ fill: '#64748b', fontSize: 11 }} width={40} />
          <Tooltip labelFormatter={(label) => truncateLabel(label, 60)} />
          <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={manyOptions ? 32 : narrow ? 28 : 48}>
            {data.map((entry, index) => (
              <Cell key={`bar-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )

  if (centered) {
    return <div className="flex w-full justify-center">{barChart}</div>
  }

  return barChart
}

function QuestionAnalyticsCard({ question: q }) {
  const isSummary = q.chart_type === 'summary'
  const manyLegendItems = (q.breakdown?.length ?? 0) > 6
  const chartLabel =
    q.chart_type === 'pie' ? 'Pie chart' : q.chart_type === 'bar' ? 'Bar chart' : 'Response summary'

  return (
    <SurfaceCard className="overflow-hidden !p-0">
      <div className="border-b border-slate-100 px-5 py-4 sm:px-6">
        <p className="text-lg font-semibold text-slate-950">
          {q.question_number}. {q.question_text}
        </p>
        <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">
          {String(q.question_type ?? 'question').replace(/_/g, ' ')} · {chartLabel}
        </p>
      </div>

      {isSummary ? (
        <div className="flex min-h-[min(480px,calc(100vh-18rem))] items-center justify-center px-6 py-10 sm:px-8 sm:py-12">
          <TextSummaryPanel total={q.total_responses} latest={q.latest_responses} />
        </div>
      ) : (
        <>
          <div className="flex min-h-[min(520px,calc(100vh-18rem))] w-full items-center justify-center px-4 py-8 sm:px-6 sm:py-10">
            <ChoiceChartPanel chartType={q.chart_type} breakdown={q.breakdown} centered />
          </div>
          <div className="border-t border-slate-100 px-6 py-5 sm:px-8 sm:py-6">
            <ChoiceLegend breakdown={q.breakdown} centered compact={manyLegendItems} />
          </div>
        </>
      )}
    </SurfaceCard>
  )
}

export default function Analytics() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
        const { data: d } = await api.get('/responses/analytics')
        if (!cancelled) setData(normalizeAnalyticsResponse(d))
      } catch {
        if (!cancelled) setError('Could not load analytics.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token, navigate])

  const questions = data?.questions || []

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Analytics"
        title="Visualize answer trends"
        description="Each question uses a layout suited to its type: totals for text, pie charts for small choice sets, and bar charts for larger option lists."
      />

      {error && (
        <SurfaceCard>
          <p className="text-sm text-rose-600">{error}</p>
        </SurfaceCard>
      )}

      {loading && (
        <SurfaceCard>
          <p className="text-sm text-slate-600">Loading analytics…</p>
        </SurfaceCard>
      )}

      {!loading &&
        questions.map((q) => <QuestionAnalyticsCard key={q.question_id} question={q} />)}

      {!loading && data && !questions.length && (
        <EmptyState
          title="No analytics yet"
          description="Add questions to the form and collect submissions to see charts here."
        />
      )}
    </div>
  )
}
