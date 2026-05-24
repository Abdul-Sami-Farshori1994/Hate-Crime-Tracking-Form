/** Inline "Other" on choice questions — stored as `Other: <text>`. */

export const OTHER_PREFIX = 'Other: '

const PRETEXT_QUESTION_KEY = 'alleged pretext of crime'

export function normalizeQuestionText(text) {
  return String(text || '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

export function isOtherOptionLabel(option) {
  return String(option).trim().toLowerCase() === 'other'
}

export function isInlineOtherExcluded(question) {
  return normalizeQuestionText(question?.question_text) === PRETEXT_QUESTION_KEY
}

export function usesInlineOther(question) {
  const type = question?.question_type
  if (!['radio', 'select', 'checkbox'].includes(type)) return false
  if (isInlineOtherExcluded(question)) return false
  const options = Array.isArray(question?.options) ? question.options.map(String) : []
  return options.some(isOtherOptionLabel)
}

export function findOtherOptionLabel(options) {
  return options.find(isOtherOptionLabel) ?? null
}

export function isOtherStoredValue(value) {
  const s = String(value ?? '').trim()
  if (s.toLowerCase() === 'other') return true
  // "Other: " becomes "Other:" after trim — match Other: with optional detail
  return /^other:\s*/i.test(s)
}

export function otherTextFromStored(value) {
  const s = String(value ?? '').trim()
  const match = s.match(/^other:\s*(.*)$/i)
  return match ? match[1].trim() : ''
}

export function formatOtherValue(text) {
  const collapsed = String(text ?? '')
    .replace(/\s+/g, ' ')
    .trim()
  return `${OTHER_PREFIX}${collapsed}`
}

/** Whether this stored value selects the given option (Other uses prefix match). */
export function choiceMatchesOption(stored, option) {
  const s = String(stored ?? '').trim()
  if (isOtherOptionLabel(option)) return isOtherStoredValue(s)
  return s === String(option).trim()
}

export function parseCheckboxWithOther(value, options) {
  const selected = []
  let otherText = ''
  let otherSelected = false
  const otherLabel = findOtherOptionLabel(options)

  let parsed = []
  try {
    parsed = value ? JSON.parse(value) : []
  } catch {
    parsed = []
  }
  if (!Array.isArray(parsed)) parsed = []

  for (const item of parsed.map(String)) {
    if (otherLabel && isOtherStoredValue(item)) {
      otherSelected = true
      otherText = otherTextFromStored(item)
    } else {
      selected.push(item)
    }
  }
  return { selected, otherText, otherSelected, otherLabel }
}

export function buildCheckboxValue(selected, otherLabel, otherSelected, otherText) {
  const items = [...selected]
  if (otherSelected && otherLabel) {
    items.push(formatOtherValue(otherText))
  }
  return JSON.stringify(items)
}

export function otherAnswerIsComplete(question, value) {
  if (!usesInlineOther(question)) return true
  const options = Array.isArray(question.options) ? question.options.map(String) : []
  const otherLabel = findOtherOptionLabel(options)
  if (!otherLabel) return true

  if (question.question_type === 'checkbox') {
    const { otherSelected, otherText } = parseCheckboxWithOther(value, options)
    if (!otherSelected) return true
    return otherText.length > 0
  }

  if (!choiceMatchesOption(value, otherLabel)) return true
  return otherTextFromStored(value).length > 0
}
