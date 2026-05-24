export const QUESTION_TYPES = ['text', 'radio', 'checkbox', 'select', 'date', 'rating', 'number']

export const QUESTION_TYPE_LABELS = {
  text: 'Long text',
  radio: 'Multiple choice',
  checkbox: 'Checkboxes',
  select: 'Dropdown',
  date: 'Date',
  rating: 'Rating (1–5)',
  number: 'Number',
}

export function optionsToLines(options) {
  if (!Array.isArray(options)) return ''
  return options.map(String).join('\n')
}

export function linesToOptions(text) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

export function getApiMessage(err, fallback) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || JSON.stringify(item)).join(', ')
  }
  if (err?.response?.status === 405) {
    return 'Method not allowed — refresh the page, then rebuild containers: docker compose up -d --build api web'
  }
  if (err?.response?.status === 404 && !detail) {
    return 'API route not found. Rebuild containers: docker compose up -d --build api web'
  }
  return fallback
}

export function buildReorderPayload(pageGroups) {
  const items = []
  for (const page of pageGroups) {
    page.questions.forEach((q, orderIndex) => {
      items.push({ id: q.id, page_id: page.id, order_index: orderIndex })
    })
  }
  return items
}

export function totalQuestionCount(pageGroups) {
  return pageGroups.reduce((n, p) => n + p.questions.length, 0)
}

export function visibleSectionCount(pageGroups) {
  return pageGroups.filter((p) => !p.is_hidden).length
}

export function isQuestionHidden(q, page) {
  return Boolean(q.is_hidden || page?.is_hidden)
}

export function firstEditableQuestion(pageGroups) {
  for (const page of pageGroups) {
    if (page.is_hidden) continue
    const q = page.questions.find((item) => !item.is_hidden)
    if (q) return q
  }
  return null
}

export function findQuestionLocation(pageGroups, questionId) {
  for (const page of pageGroups) {
    const idx = page.questions.findIndex((q) => q.id === questionId)
    if (idx >= 0) return { page, index: idx }
  }
  return null
}

export function moveQuestionInStructure(pageGroups, questionId, targetPageId, targetIndex) {
  const loc = findQuestionLocation(pageGroups, questionId)
  if (!loc) return pageGroups

  const next = pageGroups.map((p) => ({ ...p, questions: [...p.questions] }))
  const sourcePage = next.find((p) => p.id === loc.page.id)
  const [item] = sourcePage.questions.splice(loc.index, 1)

  const targetPage = next.find((p) => p.id === targetPageId)
  if (!targetPage) return pageGroups

  const insertAt = Math.max(0, Math.min(targetIndex, targetPage.questions.length))
  targetPage.questions.splice(insertAt, 0, item)
  return next
}

export function reorderWithinPage(pageGroups, pageId, fromId, toId) {
  if (fromId === toId) return pageGroups
  return pageGroups.map((page) => {
    if (page.id !== pageId) return page
    const questions = [...page.questions]
    const from = questions.findIndex((q) => q.id === fromId)
    let to = questions.findIndex((q) => q.id === toId)
    if (from < 0 || to < 0) return page
    const [item] = questions.splice(from, 1)
    if (from < to) to -= 1
    questions.splice(to, 0, item)
    return { ...page, questions }
  })
}

/**
 * Move a question to targetIndex on a page (0 = before first question).
 * Drop zones use "insert before question at index K".
 */
export function moveQuestionToIndex(pageGroups, pageId, questionId, targetIndex) {
  return pageGroups.map((page) => {
    if (page.id !== pageId) return page
    const questions = [...page.questions]
    const from = questions.findIndex((q) => q.id === questionId)
    if (from < 0) return page

    let insertAt = Math.max(0, Math.min(targetIndex, questions.length))
    if (from === insertAt) return page

    const [item] = questions.splice(from, 1)
    if (from < insertAt) insertAt -= 1
    questions.splice(insertAt, 0, item)
    return { ...page, questions }
  })
}

export function orderWithinPage(pageGroups, pageId, questionId) {
  const page = pageGroups.find((p) => p.id === pageId)
  if (!page) return 1
  const idx = page.questions.findIndex((q) => q.id === questionId)
  return idx >= 0 ? idx + 1 : page.questions.length + 1
}

export function insertOrderAfter(page, afterQuestionId) {
  if (!afterQuestionId) return page.questions.length + 1
  const idx = page.questions.findIndex((q) => q.id === afterQuestionId)
  return idx >= 0 ? idx + 2 : page.questions.length + 1
}
