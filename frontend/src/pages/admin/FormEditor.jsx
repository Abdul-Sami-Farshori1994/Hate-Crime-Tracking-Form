import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import {
  Pill,
  PrimaryButton,
  SecondaryButton,
  StatusMessage,
  TextAreaInput,
  TextInput,
  confirmAction,
} from '../../components/forms-ui'
import { useAuth } from '../../context/AuthContext'
import { adminDashboardPath } from '../../paths'
import FormEditorQuestionCard from './FormEditorQuestionCard'
import FormEditorSettingsPanel from './FormEditorSettingsPanel'
import { rulesFromQuestion, supportsBranching } from './FormEditorBranching'
import {
  buildReorderPayload,
  findQuestionLocation,
  getApiMessage,
  insertOrderAfter,
  linesToOptions,
  moveQuestionInStructure,
  optionsToLines,
  orderWithinPage,
  moveQuestionToIndex,
  totalQuestionCount,
  visibleSectionCount,
  isQuestionHidden,
  firstEditableQuestion,
} from './formEditorUtils'

function AddQuestionButton({ disabled, onClick, label = '+ Add question' }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="w-full rounded-2xl border border-dashed border-violet-300 bg-violet-50/50 px-4 py-3 text-sm font-medium text-violet-700 transition hover:border-violet-400 hover:bg-violet-50 disabled:opacity-50"
    >
      {label}
    </button>
  )
}

export default function FormEditor() {
  const { token } = useAuth()
  const [pageGroups, setPageGroups] = useState([])
  const [pageTitleBaseline, setPageTitleBaseline] = useState({})
  const [pageDescBaseline, setPageDescBaseline] = useState({})
  const [selectedId, setSelectedId] = useState(null)
  const [isAdding, setIsAdding] = useState(false)
  const [insertAfterQuestionId, setInsertAfterQuestionId] = useState(null)
  const [targetPageId, setTargetPageId] = useState(null)
  const [text, setText] = useState('')
  const [type, setType] = useState('text')
  const [optionsJson, setOptionsJson] = useState('[]')
  const [optionsLines, setOptionsLines] = useState('')
  const [branchRules, setBranchRules] = useState([])
  const [required, setRequired] = useState(false)
  const [order, setOrder] = useState(1)
  const [msg, setMsg] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [reordering, setReordering] = useState(false)
  const [savingPage, setSavingPage] = useState(null)
  const [draggingId, setDraggingId] = useState(null)
  const [dragOverId, setDragOverId] = useState(null)
  const [dragOverPageId, setDragOverPageId] = useState(null)
  const dragRef = useRef({ fromId: null, pageId: null })

  const selected = useMemo(() => {
    for (const page of pageGroups) {
      const q = page.questions.find((item) => item.id === selectedId)
      if (q) return { ...q, page_title: page.title, page_is_hidden: page.is_hidden }
    }
    return null
  }, [pageGroups, selectedId])

  const editorPageId = isAdding ? targetPageId : selected?.page_id ?? targetPageId
  const editorPage = pageGroups.find((p) => p.id === editorPageId)
  const selectedIsHidden = selected
    ? isQuestionHidden(selected, pageGroups.find((p) => p.id === selected.page_id))
    : false
  const editorPageIsHidden = Boolean(editorPage?.is_hidden)
  const showEditor =
    (isAdding && editorPage && !editorPageIsHidden) ||
    (selected && !selectedIsHidden && !editorPageIsHidden)
  const visibleSections = visibleSectionCount(pageGroups)

  const questionChoices = useMemo(() => {
    const items = []
    let n = 0
    for (const page of pageGroups) {
      if (page.is_hidden) continue
      for (const q of page.questions) {
        if (q.is_hidden) continue
        n += 1
        items.push({
          id: q.id,
          label: `Q${n} · ${q.question_text.slice(0, 72)}${q.question_text.length > 72 ? '…' : ''}`,
        })
      }
    }
    return items
  }, [pageGroups])

  const questionTotal = totalQuestionCount(pageGroups)

  const optionList = useMemo(() => linesToOptions(optionsLines), [optionsLines])

  let globalCounter = 0

  const selectQuestion = useCallback((q, groups = pageGroups) => {
    if (!q) return
    const page = groups.find((p) => p.id === q.page_id)
    if (isQuestionHidden(q, page)) return
    setIsAdding(false)
    setInsertAfterQuestionId(null)
    setSelectedId(q.id)
    setTargetPageId(q.page_id)
    setText(q.question_text)
    setType(q.question_type)
    const opts = q.options ?? []
    setOptionsJson(JSON.stringify(opts))
    setOptionsLines(optionsToLines(opts))
    setBranchRules(rulesFromQuestion(q))
    setRequired(!!q.is_required)
    setOrder(orderWithinPage(groups, q.page_id, q.id))
    setMsg(null)
    setErr(null)
  }, [pageGroups])

  const beginAddQuestion = useCallback(
    (pageId, afterQuestionId = null) => {
      const page = pageGroups.find((p) => p.id === pageId) ?? pageGroups[0]
      if (!page || page.is_hidden) return
      setIsAdding(true)
      setSelectedId(null)
      setTargetPageId(page.id)
      setInsertAfterQuestionId(afterQuestionId)
      setText('New question')
      setType('text')
      setOptionsJson('[]')
      setOptionsLines('')
      setBranchRules([])
      setRequired(false)
      setOrder(insertOrderAfter(page, afterQuestionId))
      setMsg(null)
      setErr(null)
    },
    [pageGroups],
  )

  const loadStructure = useCallback(async (keepSelection = true) => {
    const { data } = await api.get('/form/structure')
    try {
      await api.post('/form/questions/sync-global-order')
    } catch {
      /* non-fatal */
    }
    const groups = data.map((p) => ({
      id: p.id,
      title: p.title,
      description: p.description ?? '',
      order_index: p.order_index,
      is_hidden: Boolean(p.is_hidden),
      questions: [...p.questions]
        .sort((a, b) => a.order_index - b.order_index)
        .map((q) => ({ ...q, is_hidden: Boolean(q.is_hidden) })),
    }))
    setPageGroups(groups)
    const titleBaseline = {}
    const descBaseline = {}
    for (const p of groups) {
      titleBaseline[p.id] = p.title
      descBaseline[p.id] = p.description ?? ''
    }
    setPageTitleBaseline(titleBaseline)
    setPageDescBaseline(descBaseline)

    if (isAdding) {
      const page = groups.find((p) => p.id === targetPageId) ?? groups[groups.length - 1]
      if (page) {
        setTargetPageId(page.id)
        setOrder(insertOrderAfter(page, insertAfterQuestionId))
      }
      return groups
    }

    if (keepSelection && selectedId) {
      for (const page of groups) {
        const q = page.questions.find((x) => x.id === selectedId)
        if (q && !isQuestionHidden(q, page)) {
          selectQuestion(q, groups)
          return groups
        }
      }
    }

    const first = firstEditableQuestion(groups)
    if (first) selectQuestion(first, groups)
    else {
      setSelectedId(null)
      setIsAdding(false)
    }
    return groups
  }, [isAdding, selectedId, selectQuestion, targetPageId, insertAfterQuestionId])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        await loadStructure(false)
        if (!cancelled) setErr(null)
      } catch {
        if (!cancelled) setErr('Could not load form structure.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial load only
  }, [token])

  async function persistReorder(nextGroups) {
    setReordering(true)
    setErr(null)
    try {
      await api.post('/form/questions/reorder', { items: buildReorderPayload(nextGroups) })
      await loadStructure()
      setMsg('Order saved — the live form matches this layout.')
      return true
    } catch (e) {
      setErr(getApiMessage(e, 'Could not save question order.'))
      await loadStructure()
      return false
    } finally {
      setReordering(false)
    }
  }

  function handlePageTitleChange(pageId, title) {
    setPageGroups((prev) => prev.map((p) => (p.id === pageId ? { ...p, title } : p)))
  }

  function handlePageDescriptionChange(pageId, description) {
    setPageGroups((prev) => prev.map((p) => (p.id === pageId ? { ...p, description } : p)))
  }

  async function savePageField(pageId, field) {
    const page = pageGroups.find((p) => p.id === pageId)
    if (!page || page.is_hidden) return

    if (field === 'title') {
      const trimmed = page.title.trim()
      if (!trimmed) {
        setErr('Page title cannot be empty.')
        setPageGroups((prev) =>
          prev.map((p) => (p.id === pageId ? { ...p, title: pageTitleBaseline[pageId] || p.title } : p)),
        )
        return
      }
      if (trimmed === pageTitleBaseline[pageId]) return
      setSavingPage(`${pageId}-title`)
      try {
        await api.patch(`/form/pages/${pageId}`, { title: trimmed })
        setPageTitleBaseline((prev) => ({ ...prev, [pageId]: trimmed }))
        setMsg('Page saved.')
      } catch (e) {
        setErr(getApiMessage(e, 'Could not save page title.'))
        setPageGroups((prev) =>
          prev.map((p) => (p.id === pageId ? { ...p, title: pageTitleBaseline[pageId] } : p)),
        )
      } finally {
        setSavingPage(null)
      }
      return
    }

    const desc = (page.description ?? '').trim()
    const baseline = (pageDescBaseline[pageId] ?? '').trim()
    if (desc === baseline) return
    setSavingPage(`${pageId}-desc`)
    try {
      await api.patch(`/form/pages/${pageId}`, { description: desc || null })
      setPageDescBaseline((prev) => ({ ...prev, [pageId]: desc }))
      setMsg('Page description saved.')
    } catch (e) {
      setErr(getApiMessage(e, 'Could not save page description.'))
      setPageGroups((prev) =>
        prev.map((p) => (p.id === pageId ? { ...p, description: pageDescBaseline[pageId] } : p)),
      )
    } finally {
      setSavingPage(null)
    }
  }

  async function handleAddPage() {
    setSaving(true)
    setErr(null)
    try {
      const { data: page } = await api.post('/form/pages', { title: 'New page' })
      await loadStructure(false)
      beginAddQuestion(page.id)
      setMsg('Page added. Add your first question below.')
    } catch (e) {
      setErr(getApiMessage(e, 'Could not add page.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleHideSection(page) {
    if (visibleSections <= 1 && !page.is_hidden) {
      setErr('You must keep at least one visible section on the form.')
      return
    }
    if (page.is_hidden) return
    const questionCount = page.questions.length
    const label = page.title.trim() || `Section ${pageGroups.findIndex((p) => p.id === page.id) + 1}`
    const ok = confirmAction(
      `Hide Section "${label}"?\n\n` +
        (questionCount > 0
          ? `This hides ${questionCount} question${questionCount === 1 ? '' : 's'} on this section from the live form. `
          : '') +
        'Historical responses are kept. The section stays here with a Hidden status until you unhide it.',
    )
    if (!ok) return

    setSaving(true)
    setErr(null)
    setMsg(null)
    try {
      await api.delete(`/form/pages/${page.id}`)
      const deletedSelected =
        selectedId && page.questions.some((q) => q.id === selectedId)
      const deletedAdding = isAdding && targetPageId === page.id
      await loadStructure(!(deletedSelected || deletedAdding))
      setMsg(`Section "${label}" hidden.`)
    } catch (e) {
      setErr(getApiMessage(e, 'Could not hide section.'))
    } finally {
      setSaving(false)
    }
  }

  function clearDragState() {
    setDraggingId(null)
    setDragOverId(null)
    setDragOverPageId(null)
    dragRef.current = { fromId: null, pageId: null }
  }

  function handleDragStart(e, questionId, pageId) {
    const page = pageGroups.find((p) => p.id === pageId)
    const q = page?.questions.find((item) => item.id === questionId)
    if (!q || isQuestionHidden(q, page) || page?.is_hidden) {
      e.preventDefault()
      return
    }
    dragRef.current = { fromId: questionId, pageId }
    setDraggingId(questionId)
    setDragOverPageId(pageId)
    setDragOverId(null)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(questionId))
  }

  function handleDragEnd() {
    clearDragState()
  }

  function handleDragOverQuestion(e, pageId, targetQuestionId) {
    e.preventDefault()
    e.stopPropagation()
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
    if (targetQuestionId !== draggingId) {
      setDragOverId(targetQuestionId)
      setDragOverPageId(pageId)
    }
  }

  async function applyQuestionMove(pageId, fromId, insertIndex) {
    const loc = findQuestionLocation(pageGroups, fromId)
    if (!loc) return

    let next
    if (loc.page.id === pageId) {
      next = moveQuestionToIndex(pageGroups, pageId, fromId, insertIndex)
    } else {
      const page = pageGroups.find((p) => p.id === pageId)
      const clamped = Math.max(0, Math.min(insertIndex, page?.questions.length ?? 0))
      next = moveQuestionInStructure(pageGroups, fromId, pageId, clamped)
    }

    setPageGroups(next)
    const ok = await persistReorder(next)
    if (ok && selectedId === fromId) {
      setOrder(orderWithinPage(next, pageId, fromId))
      if (targetPageId !== pageId) setTargetPageId(pageId)
    }
  }

  async function handleDropOnQuestion(e, pageId, targetQuestionId) {
    e.preventDefault()
    e.stopPropagation()
    const raw = e.dataTransfer?.getData('text/plain')
    const fromId = Number(raw) || dragRef.current.fromId
    clearDragState()
    if (!fromId || fromId === targetQuestionId) return

    const page = pageGroups.find((p) => p.id === pageId)
    if (!page) return
    const fromIndex = page.questions.findIndex((q) => q.id === fromId)
    const targetIndex = page.questions.findIndex((q) => q.id === targetQuestionId)
    if (targetIndex < 0) return
    // Dropping on a card below = after it; above = before it (natural up/down reorder).
    const insertIndex =
      fromIndex >= 0 && fromIndex < targetIndex ? targetIndex + 1 : targetIndex
    await applyQuestionMove(pageId, fromId, insertIndex)
  }

  function parseOptions() {
    if (!['radio', 'checkbox', 'select'].includes(type)) return null
    const options = linesToOptions(optionsLines)
    if (!options.length) throw new Error('Add at least one answer option (one per line).')
    return options
  }

  async function persistBranchRules(questionId) {
    if (!supportsBranching(type)) return
    const payload = {
      rules: branchRules
        .filter((r) => r.option_value && r.target_question_id)
        .map((r) => ({
          option_value: String(r.option_value),
          target_question_id: Number(r.target_question_id),
        })),
    }
    await api.put(`/form/questions/${questionId}/branch-rules`, payload)
  }

  async function saveNew() {
    if (!targetPageId) {
      setErr('Choose a page for the new question.')
      return
    }
    setSaving(true)
    setMsg(null)
    setErr(null)
    try {
      const options = parseOptions()
      const page = pageGroups.find((p) => p.id === targetPageId)
      if (!page) throw new Error('Page not found.')

      const { data: created } = await api.post('/form/questions', {
        page_id: targetPageId,
        question_text: text.trim() || 'New question',
        question_type: type,
        options,
        is_required: required,
      })

      let next = pageGroups.map((p) =>
        p.id === targetPageId ? { ...p, questions: [...p.questions, created] } : p,
      )
      const targetOrder = Math.max(1, Math.min(order, page.questions.length + 1))
      next = moveQuestionInStructure(next, created.id, targetPageId, targetOrder - 1)

      setIsAdding(false)
      setInsertAfterQuestionId(null)
      setSelectedId(created.id)
      setPageGroups(next)
      const ok = await persistReorder(next)
      if (!ok) return
      if (supportsBranching(type)) {
        await persistBranchRules(created.id)
      }
      await loadStructure()
      setMsg('Question added.')
    } catch (e) {
      setErr(e instanceof Error ? e.message : getApiMessage(e, 'Could not add question.'))
    } finally {
      setSaving(false)
    }
  }

  async function saveExisting() {
    if (!selected) return
    setSaving(true)
    setMsg(null)
    setErr(null)
    try {
      const options = parseOptions()
      const currentOrder = orderWithinPage(pageGroups, selected.page_id, selectedId)
      const pageChanged = targetPageId !== selected.page_id
      const orderChanged = order !== currentOrder

      await api.put(`/form/questions/${selectedId}`, {
        question_text: text,
        question_type: type,
        options,
        is_required: required,
        page_id: targetPageId,
      })

      let next = pageGroups
      if (pageChanged || orderChanged) {
        next = moveQuestionInStructure(pageGroups, selectedId, targetPageId, Math.max(0, order - 1))
      }

      if (pageChanged || orderChanged) {
        setPageGroups(next)
        const ok = await persistReorder(next)
        if (!ok) return
      }

      if (supportsBranching(type)) {
        await persistBranchRules(selectedId)
      }

      await loadStructure()
      setMsg('Saved.')
    } catch (e) {
      setErr(e instanceof Error ? e.message : getApiMessage(e, 'Save failed.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleUnhideSection(page) {
    const label = page.title.trim() || `Section ${pageGroups.findIndex((p) => p.id === page.id) + 1}`
    const questionCount = page.questions.length
    if (
      !confirmAction(
        `Unhide Section "${label}"?\n\n` +
          `This restores the section and its ${questionCount} question${questionCount === 1 ? '' : 's'} on the live form.`,
      )
    ) {
      return
    }
    setSaving(true)
    setErr(null)
    setMsg(null)
    try {
      await api.post(`/form/pages/${page.id}/restore`)
      await loadStructure(true)
      setMsg(`Section "${label}" is visible again.`)
    } catch (e) {
      setErr(getApiMessage(e, 'Could not unhide section.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleUnhideQuestion(q) {
    const page = pageGroups.find((p) => p.id === q.page_id)
    const preview = q.question_text.slice(0, 80)
    if (
      !confirmAction(
        `Unhide Question "${preview}${q.question_text.length > 80 ? '…' : ''}"?\n\n` +
          `It will appear on the live form again in section "${page?.title || 'this section'}".`,
      )
    ) {
      return
    }
    setSaving(true)
    setErr(null)
    setMsg(null)
    try {
      await api.post(`/form/questions/${q.id}/restore`)
      await loadStructure(true)
      setMsg('Question is visible again.')
    } catch (e) {
      setErr(getApiMessage(e, 'Could not unhide question.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleHideQuestion() {
    if (
      !selected ||
      !confirmAction(
        'Hide Question from the live form?\n\nHistorical responses are kept. It stays on the canvas with a Hidden status until you unhide it.',
      )
    )
      return
    setSaving(true)
    setErr(null)
    try {
      await api.delete(`/form/questions/${selectedId}`)
      setSelectedId(null)
      setMsg('Question hidden.')
      await loadStructure(false)
    } catch (e) {
      setErr(getApiMessage(e, 'Could not delete question.'))
    } finally {
      setSaving(false)
    }
  }

  function handleSave() {
    if (isAdding) saveNew()
    else saveExisting()
  }

  function handleReset() {
    if (isAdding) {
      const page = pageGroups.find((p) => p.id === targetPageId) ?? pageGroups[0]
      if (page) beginAddQuestion(page.id, insertAfterQuestionId)
      return
    }
    if (selected) selectQuestion(selected)
  }

  const busy = loading || saving || reordering
  const statusLabel = loading
    ? 'Loading…'
    : reordering
      ? 'Saving order…'
      : saving
        ? 'Saving…'
        : savingPage
          ? 'Saving page…'
          : msg
            ? 'Saved'
            : 'Ready'

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-[24px] border border-violet-200/70 bg-white px-5 py-4 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
            Form builder
          </p>
          <h2 className="text-xl font-semibold text-slate-950">Hate Crime Tracking Form</h2>
          <p className="mt-1 text-sm text-slate-600">
            Build your form like Microsoft Forms — click a question on the canvas, edit settings on the
            right.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {pageGroups.length} section{pageGroups.length === 1 ? '' : 's'} · {questionTotal} question
            {questionTotal === 1 ? '' : 's'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={msg && !err ? 'success' : 'neutral'}>{statusLabel}</Pill>
          <Link to={adminDashboardPath('preview')}>
            <SecondaryButton type="button">Preview as respondent</SecondaryButton>
          </Link>
          <SecondaryButton type="button" onClick={handleAddPage} disabled={busy}>
            + Add section
          </SecondaryButton>
        </div>
      </div>

      {err && !showEditor && <StatusMessage>{err}</StatusMessage>}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
        <div className="min-w-0 space-y-4 rounded-[28px] border border-slate-200/80 bg-slate-100/60 p-4 sm:p-6">
          <p className="text-sm text-slate-600">
            <span className="font-medium text-slate-800">Canvas</span> — click a question card to edit.
            Drag the <span className="font-medium">⋮⋮ handle</span> and drop onto another{' '}
            <span className="font-medium text-violet-700">question card</span> to reorder. Hidden items stay on
            the canvas with a <span className="font-medium text-amber-800">Hidden</span> badge — unhide to edit.
          </p>

          {loading && (
            <p className="rounded-2xl border border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
              Loading form…
            </p>
          )}

          {!loading &&
            pageGroups.map((page, pageNum) => {
              const sectionHidden = Boolean(page.is_hidden)
              return (
              <section
                key={page.id}
                className={`rounded-[24px] border bg-white shadow-sm transition ${
                  sectionHidden
                    ? 'border-amber-200/90 bg-amber-50/30'
                    : draggingId && dragOverPageId === page.id
                      ? 'border-violet-400 ring-1 ring-violet-200'
                      : 'border-slate-200'
                }`}
              >
                <header
                  className={`space-y-3 border-b px-5 py-5 sm:px-6 ${
                    sectionHidden
                      ? 'border-amber-200/80 bg-amber-50/50'
                      : 'border-slate-100 bg-gradient-to-b from-violet-50/80 to-white'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white ${
                          sectionHidden ? 'bg-amber-600' : 'bg-violet-600'
                        }`}
                      >
                        {pageNum + 1}
                      </span>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p
                            className={`text-xs font-semibold uppercase tracking-wide ${
                              sectionHidden ? 'text-amber-800' : 'text-violet-600'
                            }`}
                          >
                            Section
                          </p>
                          {sectionHidden && (
                            <Pill className="bg-amber-100 text-amber-800">Hidden</Pill>
                          )}
                        </div>
                        {savingPage?.startsWith(String(page.id)) && <Pill className="mt-1">Saving…</Pill>}
                        <p className="mt-0.5 text-xs text-slate-500">
                          {page.questions.length} question{page.questions.length === 1 ? '' : 's'}
                          {sectionHidden ? ' · hidden from live form' : ''}
                        </p>
                      </div>
                    </div>
                    {sectionHidden ? (
                      <SecondaryButton
                        type="button"
                        disabled={busy}
                        onClick={() => handleUnhideSection(page)}
                        className="shrink-0"
                      >
                        Unhide Section
                      </SecondaryButton>
                    ) : (
                      visibleSections > 1 && (
                        <SecondaryButton
                          type="button"
                          disabled={busy}
                          onClick={() => handleHideSection(page)}
                          className="shrink-0 border-rose-200 text-rose-700 hover:bg-rose-50"
                        >
                          Hide Section
                        </SecondaryButton>
                      )
                    )}
                  </div>
                  {sectionHidden ? (
                    <p className="text-sm text-amber-900/80">
                      This section is hidden from the live form. Unhide it to edit the title, description, or
                      questions.
                    </p>
                  ) : (
                    <>
                  <label className="block">
                    <span className="sr-only">Page title</span>
                    <TextInput
                      value={page.title}
                      onChange={(e) => handlePageTitleChange(page.id, e.target.value)}
                      onBlur={() => savePageField(page.id, 'title')}
                      disabled={busy}
                      className="text-lg font-semibold"
                      placeholder="Page title"
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs font-medium text-slate-500">Page description (optional)</span>
                    <TextAreaInput
                      value={page.description ?? ''}
                      onChange={(e) => handlePageDescriptionChange(page.id, e.target.value)}
                      onBlur={() => savePageField(page.id, 'description')}
                      rows={2}
                      disabled={busy}
                      className="mt-1"
                      placeholder="Short intro shown to admins; optional for respondents"
                    />
                  </label>
                    </>
                  )}
                </header>

                <ul className="space-y-3 px-4 py-5 sm:px-5">
                  {page.questions.length === 0 && (
                    <li className="list-none py-4 text-center text-sm text-slate-500">No questions yet on this page.</li>
                  )}
                  {page.questions.map((q) => {
                    globalCounter += 1
                    const globalIndex = globalCounter
                    const qHidden = isQuestionHidden(q, page)
                    return (
                      <li key={q.id} className="list-none space-y-3">
                        <FormEditorQuestionCard
                          q={q}
                          globalIndex={globalIndex}
                          branchCount={q.branch_rules?.length ?? 0}
                          isActive={q.id === selectedId && !isAdding && !qHidden}
                          isDragging={draggingId === q.id}
                          isDropTarget={dragOverId === q.id && draggingId !== q.id}
                          isHidden={qHidden}
                          sectionHidden={sectionHidden}
                          disabled={busy}
                          onSelect={selectQuestion}
                          onUnhide={handleUnhideQuestion}
                          onDragStart={(e) => handleDragStart(e, q.id, page.id)}
                          onDragEnd={handleDragEnd}
                          onDragOver={(e) => handleDragOverQuestion(e, page.id, q.id)}
                          onDragLeave={() => {
                            if (dragOverId === q.id) setDragOverId(null)
                          }}
                          onDrop={(e) => handleDropOnQuestion(e, page.id, q.id)}
                        />
                        {!sectionHidden && !qHidden && (
                          <AddQuestionButton
                            disabled={busy}
                            onClick={() => beginAddQuestion(page.id, q.id)}
                            label="+ Add question below"
                          />
                        )}
                      </li>
                    )
                  })}
                  {!sectionHidden && (
                  <li className="list-none">
                    <AddQuestionButton
                      disabled={busy}
                      onClick={() => beginAddQuestion(page.id)}
                      label={page.questions.length ? '+ Add question at end of page' : '+ Add first question'}
                    />
                  </li>
                  )}
                </ul>
              </section>
            )})}

          {!loading && !pageGroups.length && (
            <div className="rounded-2xl border border-slate-200 bg-white px-6 py-10 text-center">
              <p className="text-sm text-slate-600">No pages yet.</p>
              <PrimaryButton type="button" className="mt-4" onClick={handleAddPage}>
                Create first page
              </PrimaryButton>
            </div>
          )}
        </div>

        <div className="flex min-h-0 flex-col xl:sticky xl:top-6 xl:max-h-[calc(100vh-5.5rem)] xl:self-start">
          {showEditor && pageGroups.length > 0 ? (
            <FormEditorSettingsPanel
              isAdding={isAdding}
              selectedId={selectedId}
              editorPage={editorPage}
              pageGroups={pageGroups}
              text={text}
              setText={setText}
              type={type}
              setType={setType}
              setBranchRules={setBranchRules}
              optionsLines={optionsLines}
              setOptionsLines={setOptionsLines}
              setOptionsJson={setOptionsJson}
              branchRules={branchRules}
              optionList={optionList}
              questionChoices={questionChoices}
              required={required}
              setRequired={setRequired}
              order={order}
              setOrder={setOrder}
              targetPageId={targetPageId}
              setTargetPageId={(pid) => {
                setTargetPageId(pid)
                const page = pageGroups.find((p) => p.id === pid)
                if (page) {
                  setOrder(
                    isAdding
                      ? insertOrderAfter(page, insertAfterQuestionId)
                      : selectedId
                        ? orderWithinPage(pageGroups, pid, selectedId)
                        : page.questions.length + 1,
                  )
                }
              }}
              busy={busy}
              saving={saving}
              msg={msg}
              err={err}
              onSave={handleSave}
              onReset={handleReset}
              onCancelAdd={() => {
                setIsAdding(false)
                setInsertAfterQuestionId(null)
                setErr(null)
                setMsg(null)
              }}
              onDelete={handleHideQuestion}
              canDelete={!isAdding && !!selectedId && !selectedIsHidden && !editorPageIsHidden}
            />
          ) : (
            <div className="rounded-[24px] border border-dashed border-violet-200 bg-violet-50/40 px-6 py-12 text-center">
              <p className="text-sm font-semibold text-violet-900">Question settings</p>
              <p className="mt-2 text-sm text-slate-600">
                {selectedIsHidden || editorPageIsHidden
                  ? 'This item is hidden. Use Unhide on the canvas to edit it again.'
                  : 'Click a visible question on the canvas to edit it here, or use + Add question on a section.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
