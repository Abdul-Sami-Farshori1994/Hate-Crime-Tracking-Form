import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import {
  AppShell,
  HeroCard,
  Pill,
  PrimaryButton,
  SecondaryButton,
  SelectInput,
  StatusMessage,
  SurfaceCard,
  TextAreaInput,
  TextInput,
} from '../components/forms-ui'
import { useAuth } from '../context/AuthContext'
import { formLoginPath, thankYouPath } from '../paths'
import {
  buildBranchMap,
  sortQuestions,
  validatePathAnswers,
  visibleQuestionIds,
  visibleQuestionNumberOnPage,
} from '../utils/formFlow'
import {
  buildCheckboxValue,
  choiceMatchesOption,
  findOtherOptionLabel,
  formatOtherValue,
  isOtherOptionLabel,
  otherAnswerIsComplete,
  otherTextFromStored,
  parseCheckboxWithOther,
  usesInlineOther,
} from '../utils/otherOption'

function parseCheckboxValue(value) {
  try {
    const parsed = value ? JSON.parse(value) : []
    return Array.isArray(parsed) ? parsed.map(String) : []
  } catch {
    return []
  }
}

function answerIsMissing(question, value) {
  if (question.question_type === 'checkbox') {
    if (parseCheckboxValue(value).length === 0) return true
    return !otherAnswerIsComplete(question, value)
  }
  if (value === undefined || value === null || String(value).trim() === '') return true
  return !otherAnswerIsComplete(question, value)
}

function OtherTextField({ value, onChange, disabled, required }) {
  return (
    <TextInput
      type="text"
      className="mt-2"
      placeholder="Please specify"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      required={required}
      aria-label="Other, please specify"
    />
  )
}

function getApiMessage(err, fallback) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || item).join(' ')
  if (err?.message && !String(err.message).startsWith('Request failed with status code')) {
    return err.message
  }
  return fallback
}

/** Scroll to top after page change. Blur focused nav buttons so the browser does not keep the footer in view. */
function scrollFormToTop(anchor) {
  const el = anchor ?? document.getElementById('form-page-top')
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur()
  }
  window.scrollTo(0, 0)
  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
  if (el) {
    el.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'auto' })
  }
}

function QuestionField({ q, value, onChange, disabled = false }) {
  const type = q.question_type
  const options = Array.isArray(q.options) ? q.options.map(String) : []

  if (type === 'text') {
    return (
      <TextAreaInput
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        required={q.is_required && !disabled}
        disabled={disabled}
        placeholder="Type your answer here"
      />
    )
  }

  if (type === 'date') {
    return (
      <TextInput
        type="date"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        required={q.is_required && !disabled}
        disabled={disabled}
      />
    )
  }

  if (type === 'number') {
    return (
      <TextInput
        type="number"
        inputMode="decimal"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        required={q.is_required && !disabled}
        disabled={disabled}
        placeholder="Enter a number"
      />
    )
  }

  if (type === 'rating') {
    return (
      <div className="grid grid-cols-5 gap-2">
        {['1', '2', '3', '4', '5'].map((rating) => (
          <button
            key={rating}
            type="button"
            disabled={disabled}
            onClick={() => onChange(rating)}
            className={`rounded-2xl border px-4 py-3 text-sm font-medium transition ${
              value === rating
                ? 'border-violet-500 bg-violet-600 text-white shadow-sm'
                : 'border-slate-200 bg-white text-slate-700 hover:border-violet-200 hover:bg-violet-50'
            }`}
          >
            {rating}
          </button>
        ))}
      </div>
    )
  }

  const inlineOther = usesInlineOther(q)
  const otherLabel = findOtherOptionLabel(options)

  if (type === 'radio') {
    const selectedOption = options.find((opt) => choiceMatchesOption(value, opt)) ?? null
    const otherActive = Boolean(
      inlineOther && otherLabel && selectedOption && isOtherOptionLabel(selectedOption),
    )
    const otherText = otherActive ? otherTextFromStored(value) : ''

    return (
      <div className="space-y-3">
        {options.map((option) => {
          const checked = choiceMatchesOption(value, option)
          const isOther = isOtherOptionLabel(option)
          return (
            <div key={option}>
              <label
                className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition ${
                  checked
                    ? 'border-violet-300 bg-violet-50 text-violet-900'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-violet-200 hover:bg-violet-50/60'
                }`}
              >
                <input
                  type="radio"
                  name={`q-${q.id}`}
                  className="h-4 w-4 accent-violet-600"
                  checked={checked}
                  disabled={disabled}
                  onChange={() => {
                    if (inlineOther && isOther) onChange(formatOtherValue(''))
                    else onChange(option)
                  }}
                  required={q.is_required && !disabled && !(inlineOther && isOther)}
                />
                <span>{option}</span>
              </label>
              {inlineOther && isOther && checked && (
                <OtherTextField
                  value={otherText}
                  onChange={(text) => onChange(formatOtherValue(text))}
                  disabled={disabled}
                  required={q.is_required && !disabled}
                />
              )}
            </div>
          )
        })}
      </div>
    )
  }

  if (type === 'select') {
    const otherActive = Boolean(
      inlineOther && otherLabel && choiceMatchesOption(value ?? '', otherLabel),
    )
    const otherText = otherActive ? otherTextFromStored(value) : ''
    const selectValue = otherActive ? otherLabel : (value ?? '')

    return (
      <div className="space-y-3">
        <SelectInput
          value={selectValue}
          onChange={(e) => {
            const next = e.target.value
            if (inlineOther && otherLabel && next === otherLabel) onChange(formatOtherValue(''))
            else onChange(next)
          }}
          required={q.is_required && !disabled && !otherActive}
          disabled={disabled}
        >
          <option value="">Select an option</option>
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </SelectInput>
        {otherActive && (
          <OtherTextField
            value={otherText}
            onChange={(text) => onChange(formatOtherValue(text))}
            disabled={disabled}
            required={q.is_required && !disabled}
          />
        )}
      </div>
    )
  }

  if (type === 'checkbox') {
    const { selected, otherText, otherSelected } = parseCheckboxWithOther(value, options)

    function setCheckboxChecked(option, nextChecked) {
      if (inlineOther && isOtherOptionLabel(option)) {
        onChange(
          buildCheckboxValue(
            selected,
            otherLabel,
            nextChecked,
            nextChecked ? otherText : '',
          ),
        )
        return
      }
      const set = new Set(selected.map(String))
      if (nextChecked) set.add(option)
      else set.delete(option)
      onChange(
        buildCheckboxValue(Array.from(set), otherLabel, otherSelected, otherText),
      )
    }

    return (
      <div className="space-y-3">
        {options.map((option, optIndex) => {
          const isOther = isOtherOptionLabel(option)
          const checked = isOther
            ? otherSelected
            : selected.includes(option)
          const inputId = `q-${q.id}-cb-${optIndex}`
          return (
            <div key={option}>
              <div
                className={`flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition ${
                  checked
                    ? 'border-violet-300 bg-violet-50 text-violet-900'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-violet-200 hover:bg-violet-50/60'
                }`}
              >
                <input
                  id={inputId}
                  type="checkbox"
                  className="h-4 w-4 shrink-0 rounded accent-violet-600"
                  checked={checked}
                  disabled={disabled}
                  onChange={(e) => setCheckboxChecked(option, e.target.checked)}
                />
                <label htmlFor={inputId} className="min-w-0 flex-1 cursor-pointer">
                  {option}
                </label>
              </div>
              {inlineOther && isOther && otherSelected && (
                <OtherTextField
                  value={otherText}
                  onChange={(text) =>
                    onChange(buildCheckboxValue(selected, otherLabel, true, text))
                  }
                  disabled={disabled}
                  required={q.is_required && !disabled}
                />
              )}
            </div>
          )
        })}
      </div>
    )
  }

  return <StatusMessage>Unsupported question type: {type}</StatusMessage>
}

export default function FormPage() {
  const { token, role, logout, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [pages, setPages] = useState([])
  const [pageIndex, setPageIndex] = useState(0)
  const [orderedQuestions, setOrderedQuestions] = useState([])
  const [branchMap, setBranchMap] = useState(() => new Map())
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [consentChecked, setConsentChecked] = useState(false)
  const formTopRef = useRef(null)

  const consentRequired =
    String(import.meta.env.VITE_CONSENT_REQUIRED || '').trim().toLowerCase() === 'true'

  const safePages = Array.isArray(pages) ? pages : []
  const currentPage = safePages[pageIndex] ?? null

  const visibleIds = useMemo(
    () => visibleQuestionIds(orderedQuestions, branchMap, answers),
    [orderedQuestions, branchMap, answers],
  )

  const questionsById = useMemo(
    () => new Map(orderedQuestions.map((q) => [q.id, q])),
    [orderedQuestions],
  )

  useEffect(() => {
    if (authLoading) return
    if (!token) {
      navigate(formLoginPath(), { replace: true })
      return
    }
    if (role && role !== 'user') {
      logout().then(() => navigate(formLoginPath(), { replace: true }))
    }
  }, [token, role, logout, navigate, authLoading])

  useEffect(() => {
    if (!token || role !== 'user') return

    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const { data } = await api.get('/form/flow')
        if (cancelled) return
        if (!data?.pages || !Array.isArray(data.questions)) {
          throw new Error('Invalid form flow response')
        }
        setPages(data.pages)
        setOrderedQuestions(sortQuestions(data.questions, data.pages))
        setBranchMap(buildBranchMap(data.branches))
        setPageIndex(0)
      } catch {
        if (!cancelled) {
          setPages([])
          setOrderedQuestions([])
          setBranchMap(new Map())
          setError(
            'Could not load the form. Run docker compose up -d --build api, restart Vite (npm run dev), and refresh. Stop any old local API on ports 8000–8001 if you still see errors.',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [token, role])

  useEffect(() => {
    if (!currentPage?.id || loading) return
    const pageQuestions = orderedQuestions
      .filter((q) => q.page_id === currentPage.id && visibleIds.has(q.id))
      .sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0))
    setQuestions(pageQuestions)
  }, [currentPage?.id, orderedQuestions, visibleIds, loading])

  const pageScrollKey = currentPage ? `${pageIndex}-${currentPage.id}` : `page-${pageIndex}`

  useLayoutEffect(() => {
    if (loading) return
    const run = () => scrollFormToTop(formTopRef.current)
    run()
    const t0 = window.setTimeout(run, 0)
    const t1 = window.setTimeout(run, 100)
    const t2 = window.setTimeout(run, 300)
    return () => {
      window.clearTimeout(t0)
      window.clearTimeout(t1)
      window.clearTimeout(t2)
    }
  }, [pageScrollKey, loading])

  const progress = useMemo(() => {
    if (!safePages.length) return 0
    return Math.round(((pageIndex + 1) / safePages.length) * 100)
  }, [pageIndex, safePages.length])

  const completedRequired = useMemo(
    () => questions.filter((question) => question.is_required && !answerIsMissing(question, answers[question.id])).length,
    [answers, questions],
  )

  function setAnswer(id, value) {
    setAnswers((prev) => ({ ...prev, [id]: value }))
  }

  function handleLogout() {
    logout()
    navigate(formLoginPath(), { replace: true })
  }

  function pageHasVisibleQuestions(pageId, ids = visibleIds) {
    return orderedQuestions.some((q) => q.page_id === pageId && ids.has(q.id))
  }

  function goNext() {
    try {
      setError(null)
      for (const question of questions) {
        if (question.is_required && answerIsMissing(question, answers[question.id])) {
          throw new Error(`Please answer required question: ${question.question_text}`)
        }
      }
      if (pageIndex < safePages.length - 1) {
        let next = pageIndex + 1
        while (next < safePages.length && !pageHasVisibleQuestions(safePages[next].id)) {
          next += 1
        }
        setPageIndex(next)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Please finish the required questions on this page.')
    }
  }

  function goBack() {
    if (pageIndex > 0) {
      setError(null)
      let prev = pageIndex - 1
      while (prev > 0 && !pageHasVisibleQuestions(safePages[prev].id)) {
        prev -= 1
      }
      setPageIndex(prev)
    }
  }

  async function submit() {
    setSubmitting(true)
    setError(null)
    try {
      const pathIds = validatePathAnswers(orderedQuestions, branchMap, answers, questionsById)

      if (consentRequired && !consentChecked) {
        throw new Error('Please confirm consent before submitting.')
      }

      const payload = {
        answers: pathIds
          .filter((questionId) => {
            const q = questionsById.get(questionId)
            if (!q) return false
            return q.is_required || !answerIsMissing(q, answers[questionId])
          })
          .map((questionId) => ({
            question_id: questionId,
            answer_value: String(answers[questionId] ?? ''),
          })),
        consent_acknowledged: consentChecked,
      }

      await api.post('/responses/submit', payload)
      navigate(thankYouPath())
    } catch (err) {
      setError(err instanceof Error ? err.message : getApiMessage(err, 'Submit failed.'))
    } finally {
      setSubmitting(false)
    }
  }

  if (!token || role !== 'user') return null

  if (loading) {
    return (
      <AppShell width="form">
        <div className="mx-auto max-w-4xl space-y-6">
          <HeroCard
            eyebrow="Loading"
            title="Preparing the report form"
            description="Please wait while the form pages and questions are loaded."
          />
          <SurfaceCard>
            <p className="text-sm text-slate-600">Loading form…</p>
          </SurfaceCard>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell width="form">
      <div className="mx-auto max-w-4xl space-y-6">
        <div
          id="form-page-top"
          ref={formTopRef}
          className="h-0 w-full scroll-mt-0"
          tabIndex={-1}
          aria-hidden
        />
        <HeroCard
          showLogo
          logoSize="lg"
          title="Hate Crime Tracking"
          centered
          titleClassName="bg-gradient-to-r from-violet-700 via-violet-600 to-fuchsia-600 bg-clip-text text-transparent"
          subtitle="This is a joint project to track hate crimes against minorities in India"
          description="Please don't hesitate to take a mental (and physical) break while working through cases of violence. We deeply appreciate your contribution to this task."
        />

        <SurfaceCard className="flex flex-wrap items-center justify-end gap-3">
          <SecondaryButton type="button" onClick={handleLogout}>
            Sign out
          </SecondaryButton>
        </SurfaceCard>

        <SurfaceCard>
          <div className="flex flex-wrap gap-2">
            {safePages.map((page, index) => (
              <Pill key={page.id} tone={index === pageIndex ? 'brand' : 'neutral'}>
                {index + 1}. {page.title}
              </Pill>
            ))}
          </div>
          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              <span>Completion</span>
              <span>{progress}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-500 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </SurfaceCard>

        {currentPage && (
          <SurfaceCard className="border-violet-200">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
                Page {pageIndex + 1}
              </p>
              <h2 className="text-2xl font-semibold text-slate-950">{currentPage.title}</h2>
              {currentPage.description && (
                <p className="text-sm leading-6 text-slate-600">{currentPage.description}</p>
              )}
            </div>
          </SurfaceCard>
        )}

        {questions.map((question) => {
          const qNum = visibleQuestionNumberOnPage(questions, question)
          return (
            <SurfaceCard
              key={question.id}
              className={question.is_required ? 'border-violet-200' : ''}
            >
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Pill tone="brand">Question {qNum ?? '—'}</Pill>
                  {question.is_required && <Pill tone="success">Required</Pill>}
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg font-medium text-slate-950">{question.question_text}</h3>
                  {question.help_text && (
                    <p className="text-sm text-slate-600">{question.help_text}</p>
                  )}
                </div>
                <QuestionField
                  q={question}
                  value={answers[question.id]}
                  onChange={(value) => setAnswer(question.id, value)}
                />
              </div>
            </SurfaceCard>
          )
        })}

        {!questions.length && (
          <SurfaceCard>
            <p className="text-sm text-slate-600">
              No questions to show on this step based on your earlier answers.
            </p>
            {pageIndex < safePages.length - 1 && (
              <PrimaryButton type="button" className="mt-4" onClick={goNext}>
                Continue
              </PrimaryButton>
            )}
          </SurfaceCard>
        )}

        {error && <StatusMessage>{error}</StatusMessage>}

        {consentRequired && pageIndex === safePages.length - 1 && questions.length > 0 && (
          <SurfaceCard>
            <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-700">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                aria-describedby="consent-description"
              />
              <span id="consent-description">
                I understand this information will be stored securely and used only for hate crime
                tracking and reporting purposes.
              </span>
            </label>
          </SurfaceCard>
        )}

        <SurfaceCard className="flex flex-wrap items-center justify-between gap-3">
          <SecondaryButton type="button" onClick={goBack} disabled={pageIndex === 0}>
            Back
          </SecondaryButton>

          {pageIndex < safePages.length - 1 ? (
            <PrimaryButton type="button" onClick={goNext}>
              Save and continue
            </PrimaryButton>
          ) : (
            <PrimaryButton
              type="button"
              tone="success"
              onClick={submit}
              disabled={submitting || (consentRequired && !consentChecked)}
            >
              {submitting ? 'Submitting…' : 'Submit report'}
            </PrimaryButton>
          )}
        </SurfaceCard>
      </div>
    </AppShell>
  )
}

