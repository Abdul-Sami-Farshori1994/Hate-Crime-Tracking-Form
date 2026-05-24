import { Pill, SecondaryButton } from '../../components/forms-ui'
import FormEditorQuestionPreview from './FormEditorQuestionPreview'
import { QUESTION_TYPE_LABELS } from './formEditorUtils'

function DragHandle({ onDragStart, onDragEnd, disabled }) {
  return (
    <span
      draggable={!disabled}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-400 ${
        disabled ? 'cursor-not-allowed opacity-40' : 'cursor-grab active:cursor-grabbing'
      }`}
      aria-label={disabled ? 'Reorder disabled while hidden' : 'Drag to reorder — drop on another question card'}
      title={disabled ? 'Unhide to reorder' : 'Drag to reorder'}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
        <circle cx="5" cy="4" r="1.25" />
        <circle cx="11" cy="4" r="1.25" />
        <circle cx="5" cy="8" r="1.25" />
        <circle cx="11" cy="8" r="1.25" />
        <circle cx="5" cy="12" r="1.25" />
        <circle cx="11" cy="12" r="1.25" />
      </svg>
    </span>
  )
}

export default function FormEditorQuestionCard({
  q,
  globalIndex,
  branchCount,
  isActive,
  isDragging,
  isDropTarget,
  isHidden,
  sectionHidden,
  disabled,
  onSelect,
  onUnhide,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDragLeave,
  onDrop,
}) {
  const typeLabel = QUESTION_TYPE_LABELS[q.question_type] ?? q.question_type
  const options = Array.isArray(q.options) ? q.options.map(String) : []
  const interactionDisabled = disabled || isHidden

  return (
    <article
      onDragOver={isHidden ? undefined : onDragOver}
      onDragLeave={isHidden ? undefined : onDragLeave}
      onDrop={isHidden ? undefined : onDrop}
      className={`group relative overflow-hidden rounded-2xl border bg-white shadow-sm transition ${
        isHidden
          ? 'border-amber-200/90 bg-amber-50/40 opacity-90'
          : isDropTarget
            ? 'border-violet-500 ring-2 ring-violet-300 ring-offset-2'
            : isActive
              ? 'border-violet-400 ring-2 ring-violet-200'
              : 'border-slate-200 hover:border-violet-200 hover:shadow-md'
      } ${isDragging ? 'opacity-40' : ''}`}
    >
      {isActive && !isDropTarget && !isHidden && (
        <div className="absolute left-0 top-0 h-full w-1 bg-violet-500" aria-hidden />
      )}
      <div className="flex gap-2 p-4 sm:p-5">
        <DragHandle
          disabled={interactionDisabled}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone={isHidden ? 'neutral' : 'brand'}>Q{globalIndex}</Pill>
            {isHidden && (
              <Pill className="bg-amber-100 text-amber-800">Hidden</Pill>
            )}
            <Pill>{typeLabel}</Pill>
            <Pill tone={q.is_required ? 'success' : 'neutral'}>
              {q.is_required ? 'Required' : 'Optional'}
            </Pill>
            {branchCount > 0 && (
              <Pill tone="brand">
                {branchCount} rule{branchCount === 1 ? '' : 's'}
              </Pill>
            )}
          </div>
          <p className="mt-3 text-base font-semibold leading-snug text-slate-950">{q.question_text}</p>
          <FormEditorQuestionPreview questionType={q.question_type} options={options} />
          {isHidden ? (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <p className="text-xs text-amber-900/80">
                {sectionHidden
                  ? 'Hidden because this section is hidden. Unhide the section to edit this question.'
                  : 'Hidden from the live form. Unhide to edit or reorder.'}
              </p>
              {!sectionHidden && onUnhide && (
                <SecondaryButton type="button" disabled={disabled} onClick={() => onUnhide(q)}>
                  Unhide Question
                </SecondaryButton>
              )}
            </div>
          ) : (
            <button
              type="button"
              className="mt-3 block w-full text-left"
              onClick={() => onSelect(q)}
              disabled={interactionDisabled}
            >
              <p className="text-xs font-medium text-violet-600">
                {isDropTarget
                  ? 'Release to place question here'
                  : isActive
                    ? 'Editing in settings panel →'
                    : 'Click to edit · drag handle onto another question to reorder'}
              </p>
            </button>
          )}
        </div>
      </div>
    </article>
  )
}
