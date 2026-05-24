/** Microsoft Forms-style branching: hide branch targets until their parent answer is set. */

import { choiceMatchesOption, otherAnswerIsComplete } from './otherOption'

export function buildBranchMap(branches) {
  const map = new Map()
  if (!Array.isArray(branches)) return map
  for (const rule of branches) {
    if (!map.has(rule.source_ms_forms_id)) {
      map.set(rule.source_ms_forms_id, new Map())
    }
    map.get(rule.source_ms_forms_id).set(rule.option_value, rule.target_ms_forms_id)
  }
  return map
}

/** Order for branching + submit path: sections (pages) first, then question order in editor. */
export function sortQuestions(questions, pages = null) {
  if (!Array.isArray(questions)) return []
  if (Array.isArray(pages) && pages.length > 0) {
    const pageOrder = new Map(pages.map((p) => [p.id, p.order_index ?? 0]))
    return [...questions].sort((a, b) => {
      const pa = pageOrder.get(a.page_id) ?? 0
      const pb = pageOrder.get(b.page_id) ?? 0
      if (pa !== pb) return pa - pb
      const oa = a.order_index ?? a.global_order ?? a.id
      const ob = b.order_index ?? b.global_order ?? b.id
      return oa - ob
    })
  }
  return [...questions].sort((a, b) => {
    const ga = a.global_order ?? a.order_index ?? a.id
    const gb = b.global_order ?? b.order_index ?? b.id
    return ga - gb
  })
}

function branchTargetMsIds(branchMap) {
  const targets = new Set()
  for (const rules of branchMap.values()) {
    for (const target of rules.values()) {
      targets.add(target)
    }
  }
  return targets
}

function answerMatchesBranchOption(raw, option, questionType) {
  if (raw === undefined || raw === null) return false
  if (questionType === 'checkbox') {
    try {
      const parsed = raw ? JSON.parse(raw) : []
      if (!Array.isArray(parsed)) return false
      return parsed.map(String).some((item) => choiceMatchesOption(item, option))
    } catch {
      return false
    }
  }
  if (typeof raw === 'string' && raw.startsWith('[')) return false
  const s = String(raw).trim()
  if (!s) return false
  return choiceMatchesOption(s, option)
}

function branchTargetIsVisible(q, branchMap, byMs, answersById) {
  for (const [sourceMs, rules] of branchMap) {
    const sourceQ = byMs.get(sourceMs)
    if (!sourceQ) continue
    const raw = answersById[sourceQ.id]
    for (const [option, targetMs] of rules) {
      if (
        targetMs === q.ms_forms_id &&
        answerMatchesBranchOption(raw, option, sourceQ.question_type)
      ) {
        return true
      }
    }
  }
  return false
}

/** Non-target questions are always visible; branch targets appear only when triggered. */
export function visibleQuestionIds(ordered, branchMap, answersById) {
  if (!ordered.length) return new Set()

  const targets = branchTargetMsIds(branchMap)
  const byMs = new Map(ordered.map((q) => [q.ms_forms_id, q]))
  const visible = new Set()

  for (const q of ordered) {
    if (!q.ms_forms_id || !targets.has(q.ms_forms_id)) {
      visible.add(q.id)
      continue
    }
    if (branchTargetIsVisible(q, branchMap, byMs, answersById)) {
      visible.add(q.id)
    }
  }

  return visible
}

/** 1-based label among visible questions on the current page (not original form index). */
export function visibleQuestionNumberOnPage(visiblePageQuestions, question) {
  const idx = visiblePageQuestions.findIndex((q) => q.id === question.id)
  return idx >= 0 ? idx + 1 : null
}

function branchTarget(branchMap, msFormsId, answer, questionType) {
  const rules = branchMap.get(msFormsId)
  if (!rules || answer === undefined || answer === null) {
    return null
  }
  for (const [option, target] of rules) {
    if (answerMatchesBranchOption(answer, option, questionType)) {
      return target
    }
  }
  return null
}

export function nextMsFormsId(ordered, branchMap, currentMsId, answer, questionType) {
  const jump = branchTarget(branchMap, currentMsId, answer, questionType)
  if (jump) return jump
  const idx = ordered.findIndex((q) => q.ms_forms_id === currentMsId)
  if (idx < 0) return null
  return ordered[idx + 1]?.ms_forms_id ?? null
}

/** Question ids included in submit (visible / active branch path). */
export function pathQuestionIds(ordered, branchMap, answersById) {
  const visible = visibleQuestionIds(ordered, branchMap, answersById)
  return ordered.filter((q) => visible.has(q.id)).map((q) => q.id)
}

export function validatePathAnswers(ordered, branchMap, answersById, questionsById) {
  const path = pathQuestionIds(ordered, branchMap, answersById)
  for (const qid of path) {
    const q = questionsById.get(qid)
    if (!q?.is_required) continue
    const raw = answersById[qid]
    if (q.question_type === 'checkbox') {
      try {
        const parsed = raw ? JSON.parse(raw) : []
        if (!Array.isArray(parsed) || parsed.length === 0) {
          throw new Error(`Please answer required question: ${q.question_text}`)
        }
      } catch (e) {
        if (e instanceof Error && e.message.startsWith('Please answer')) throw e
        throw new Error(`Please answer required question: ${q.question_text}`)
      }
    } else if (raw === undefined || raw === null || String(raw).trim() === '') {
      throw new Error(`Please answer required question: ${q.question_text}`)
    }
    if (!otherAnswerIsComplete(q, raw)) {
      throw new Error(`Please specify your Other answer for: ${q.question_text}`)
    }
  }
  return path
}
