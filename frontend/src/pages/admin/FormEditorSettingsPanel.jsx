import {
  FormLabel,
  Pill,
  PrimaryButton,
  SecondaryButton,
  SelectInput,
  StatusMessage,
  SurfaceCard,
  TextAreaInput,
  TextInput,
} from '../../components/forms-ui'
import FormEditorBranching, { supportsBranching } from './FormEditorBranching'
import { QUESTION_TYPES, QUESTION_TYPE_LABELS } from './formEditorUtils'

function SettingsSection({ title, hint, children }) {
  return (
    <section className="space-y-3 rounded-2xl border border-slate-100 bg-slate-50/50 p-4">
      <div>
        <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
        {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
      </div>
      {children}
    </section>
  )
}

export default function FormEditorSettingsPanel({
  isAdding,
  selectedId,
  editorPage,
  pageGroups,
  text,
  setText,
  type,
  setType,
  setBranchRules,
  optionsLines,
  setOptionsLines,
  setOptionsJson,
  branchRules,
  optionList,
  questionChoices,
  required,
  setRequired,
  order,
  setOrder,
  targetPageId,
  setTargetPageId,
  busy,
  saving,
  msg,
  err,
  onSave,
  onReset,
  onCancelAdd,
  onDelete,
  canDelete,
}) {
  const pageMax = isAdding
    ? (editorPage?.questions.length ?? 0) + 1
    : Math.max(1, editorPage?.questions.length ?? 1)

  return (
    <SurfaceCard className="flex h-full max-h-[calc(100vh-5.5rem)] min-h-[280px] flex-col overflow-hidden border-violet-200/80 shadow-md">
      {/* Header — fixed */}
      <div className="shrink-0 border-b border-slate-100 px-5 pb-4 pt-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-violet-600">Settings</p>
        <h3 className="text-lg font-semibold text-slate-950">
          {isAdding ? 'New question' : 'Question settings'}
        </h3>
        <p className="mt-1 text-sm text-slate-600">
          {isAdding
            ? 'Fill in the details below, then click Add question at the bottom.'
            : 'Update fields below, then Save changes.'}
        </p>
        {editorPage && <Pill className="mt-2">{editorPage.title}</Pill>}
      </div>

      {/* Scrollable fields */}
      <div
        className="settings-panel-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4"
        role="region"
        aria-label="Question settings — scroll for more"
      >
        <div className="space-y-4 text-sm">
          <SettingsSection title="Question" hint="What respondents will see.">
            <FormLabel label="Question text">
              <TextAreaInput
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={4}
                disabled={busy}
                placeholder="e.g. Please describe the incident"
              />
            </FormLabel>

            <FormLabel label="Answer type">
              <SelectInput
                value={type}
                onChange={(e) => {
                  const nextType = e.target.value
                  setType(nextType)
                  if (!supportsBranching(nextType)) setBranchRules([])
                }}
                disabled={busy}
              >
                {QUESTION_TYPES.map((questionType) => (
                  <option key={questionType} value={questionType}>
                    {QUESTION_TYPE_LABELS[questionType] ?? questionType}
                  </option>
                ))}
              </SelectInput>
            </FormLabel>

            <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-700">
              <input
                type="checkbox"
                className="h-4 w-4 rounded accent-violet-600"
                checked={required}
                onChange={(e) => setRequired(e.target.checked)}
                disabled={busy}
              />
              Required question
            </label>
          </SettingsSection>

          {['radio', 'checkbox', 'select'].includes(type) && (
            <SettingsSection title="Answer choices" hint="One option per line, like Microsoft Forms.">
              <TextAreaInput
                value={optionsLines}
                onChange={(e) => {
                  setOptionsLines(e.target.value)
                  setOptionsJson(
                    JSON.stringify(
                      e.target.value
                        .split('\n')
                        .map((line) => line.trim())
                        .filter(Boolean),
                    ),
                  )
                }}
                rows={6}
                disabled={busy}
                placeholder={'Yes\nNo\nOther'}
              />
            </SettingsSection>
          )}

          {supportsBranching(type) && (
            <SettingsSection title="Conditional logic" hint="Show a follow-up question when an answer is chosen.">
              <FormEditorBranching
                branchRules={branchRules}
                setBranchRules={setBranchRules}
                optionList={optionList}
                questionChoices={questionChoices}
                sourceQuestionId={isAdding ? null : selectedId}
                disabled={busy}
              />
            </SettingsSection>
          )}

          <SettingsSection title="Placement" hint="Which section and position on that section.">
            <FormLabel label="Page (section)">
              <SelectInput
                value={targetPageId ?? ''}
                onChange={(e) => setTargetPageId(Number(e.target.value))}
                disabled={busy}
              >
                {pageGroups.map((p, i) => (
                  <option key={p.id} value={p.id}>
                    Section {i + 1}: {p.title}
                  </option>
                ))}
              </SelectInput>
            </FormLabel>

            <FormLabel
              label="Position on page"
              hint={`1 = first on page, up to ${pageMax}. Or drag onto another question card.`}
            >
              <TextInput
                type="number"
                min={1}
                max={pageMax}
                value={order}
                onChange={(e) => setOrder(Math.max(1, Number(e.target.value) || 1))}
                disabled={busy}
              />
            </FormLabel>
          </SettingsSection>
        </div>
      </div>

      {/* Footer — fixed (Save always visible) */}
      <div className="shrink-0 space-y-3 border-t border-slate-200 bg-slate-50/95 px-5 py-4">
        <p className="text-center text-[11px] text-slate-400 xl:hidden">Scroll up for more fields ↑</p>
        <div className="flex flex-wrap gap-2">
          <PrimaryButton type="button" onClick={onSave} disabled={busy} className="flex-1 sm:flex-none">
            {saving ? 'Saving…' : isAdding ? 'Add question' : 'Save changes'}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={onReset} disabled={busy}>
            Reset
          </SecondaryButton>
          {isAdding && (
            <SecondaryButton type="button" onClick={onCancelAdd} disabled={busy}>
              Cancel
            </SecondaryButton>
          )}
          {!isAdding && canDelete && (
            <SecondaryButton type="button" onClick={onDelete} disabled={busy} className="text-rose-700">
              Hide Question
            </SecondaryButton>
          )}
        </div>
        {msg && <StatusMessage tone="success">{msg}</StatusMessage>}
        {err && <StatusMessage>{err}</StatusMessage>}
      </div>
    </SurfaceCard>
  )
}
