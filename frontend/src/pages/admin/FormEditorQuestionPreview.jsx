/** Read-only preview of how a question looks to respondents (Microsoft Forms–style card body). */

export default function FormEditorQuestionPreview({ questionType, options = [] }) {
  const opts = Array.isArray(options) ? options.map(String).slice(0, 4) : []
  const more = (Array.isArray(options) ? options.length : 0) - opts.length

  if (questionType === 'radio') {
    return (
      <div className="mt-3 space-y-2 pointer-events-none" aria-hidden>
        {opts.map((opt) => (
          <div key={opt} className="flex items-center gap-2.5 text-sm text-slate-600">
            <span className="h-4 w-4 shrink-0 rounded-full border-2 border-slate-300" />
            <span>{opt}</span>
          </div>
        ))}
        {more > 0 && <p className="text-xs text-slate-400">+{more} more option{more === 1 ? '' : 's'}</p>}
        {!opts.length && <p className="text-xs italic text-slate-400">Add answer options in the panel →</p>}
      </div>
    )
  }

  if (questionType === 'checkbox') {
    return (
      <div className="mt-3 space-y-2 pointer-events-none" aria-hidden>
        {opts.map((opt) => (
          <div key={opt} className="flex items-center gap-2.5 text-sm text-slate-600">
            <span className="h-4 w-4 shrink-0 rounded border-2 border-slate-300" />
            <span>{opt}</span>
          </div>
        ))}
        {more > 0 && <p className="text-xs text-slate-400">+{more} more</p>}
        {!opts.length && <p className="text-xs italic text-slate-400">Add answer options in the panel →</p>}
      </div>
    )
  }

  if (questionType === 'select') {
    return (
      <div className="mt-3 pointer-events-none" aria-hidden>
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400">
          {opts[0] || 'Choose an option'}
        </div>
      </div>
    )
  }

  if (questionType === 'date') {
    return (
      <div className="mt-3 pointer-events-none" aria-hidden>
        <div className="max-w-xs rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400">
          mm/dd/yyyy
        </div>
      </div>
    )
  }

  if (questionType === 'rating') {
    return (
      <div className="mt-3 flex gap-1 pointer-events-none" aria-hidden>
        {[1, 2, 3, 4, 5].map((n) => (
          <span
            key={n}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-400"
          >
            {n}
          </span>
        ))}
      </div>
    )
  }

  if (questionType === 'number') {
    return (
      <div className="mt-3 pointer-events-none" aria-hidden>
        <div className="max-w-[8rem] rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400">
          0
        </div>
      </div>
    )
  }

  return (
    <div className="mt-3 pointer-events-none" aria-hidden>
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-400">
        Long answer text…
      </div>
    </div>
  )
}
