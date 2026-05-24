import { Pill, SecondaryButton, SelectInput, SurfaceCard } from '../../components/forms-ui'

/**
 * @typedef {{ id?: number, option_value: string, target_question_id: number | '' }} BranchRuleDraft
 */

export function supportsBranching(questionType) {
  return ['radio', 'select', 'checkbox'].includes(questionType)
}

export function rulesFromQuestion(q) {
  if (!q?.branch_rules?.length) return []
  return q.branch_rules.map((r) => ({
    id: r.id,
    option_value: r.option_value,
    target_question_id: r.target_question_id ?? '',
  }))
}

export default function FormEditorBranching({
  branchRules,
  setBranchRules,
  optionList,
  questionChoices,
  sourceQuestionId,
  disabled,
}) {
  function updateRule(index, patch) {
    setBranchRules((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  function removeRule(index) {
    setBranchRules((prev) => prev.filter((_, i) => i !== index))
  }

  function addRule() {
    const firstOption = optionList[0] ?? ''
    const firstTarget = questionChoices.find((q) => q.id !== sourceQuestionId)?.id ?? ''
    setBranchRules((prev) => [
      ...prev,
      { option_value: firstOption, target_question_id: firstTarget },
    ])
  }

  const targets = questionChoices.filter((q) => q.id !== sourceQuestionId)

  return (
    <SurfaceCard className="border-violet-200 bg-violet-50/30">
      <div className="space-y-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-slate-950">Conditional logic</h4>
            <Pill tone="brand">Go to question</Pill>
          </div>
          <p className="text-sm leading-6 text-slate-600">
            When the respondent picks an answer, show a specific follow-up question (like Microsoft
            Forms or Google Forms branching). Other questions stay hidden until their rule matches.
          </p>
        </div>

        {!optionList.length && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Add at least one answer option above before creating branch rules.
          </p>
        )}

        {branchRules.length > 0 && (
          <ul className="space-y-3">
            {branchRules.map((rule, index) => (
              <li
                key={rule.id ?? `draft-${index}`}
                className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <div className="grid gap-3 sm:grid-cols-[1fr_1.4fr_auto] sm:items-end">
                  <label className="block text-sm">
                    <span className="mb-1.5 block font-medium text-slate-700">If answer is</span>
                    {optionList.length > 0 ? (
                      <SelectInput
                        value={rule.option_value}
                        onChange={(e) => updateRule(index, { option_value: e.target.value })}
                        disabled={disabled}
                      >
                        {optionList.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </SelectInput>
                    ) : (
                      <input
                        className="w-full rounded-2xl border border-slate-200 px-3 py-2.5 text-sm"
                        value={rule.option_value}
                        onChange={(e) => updateRule(index, { option_value: e.target.value })}
                        disabled={disabled}
                        placeholder="Option text"
                      />
                    )}
                  </label>

                  <label className="block text-sm">
                    <span className="mb-1.5 block font-medium text-slate-700">Go to question</span>
                    <SelectInput
                      value={rule.target_question_id}
                      onChange={(e) =>
                        updateRule(index, { target_question_id: Number(e.target.value) })
                      }
                      disabled={disabled || !targets.length}
                    >
                      <option value="">Select question…</option>
                      {targets.map((q) => (
                        <option key={q.id} value={q.id}>
                          {q.label}
                        </option>
                      ))}
                    </SelectInput>
                  </label>

                  <SecondaryButton
                    type="button"
                    className="shrink-0"
                    onClick={() => removeRule(index)}
                    disabled={disabled}
                  >
                    Remove
                  </SecondaryButton>
                </div>
              </li>
            ))}
          </ul>
        )}

        <SecondaryButton
          type="button"
          onClick={addRule}
          disabled={disabled || !targets.length || !optionList.length}
        >
          + Add branch rule
        </SecondaryButton>
      </div>
    </SurfaceCard>
  )
}
