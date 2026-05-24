import { cloneElement, isValidElement, useId } from 'react'
import { Link } from 'react-router-dom'
import AppLogo from './AppLogo'

function cn(...parts) {
  return parts.filter(Boolean).join(' ')
}

const inputClassName =
  'w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-100'

export function AppShell({ children, width = 'wide', className = '' }) {
  const widthClass =
    width === 'narrow'
      ? 'max-w-5xl'
      : width === 'form'
        ? 'max-w-4xl'
        : width === 'full'
          ? 'max-w-[min(100%,90rem)]'
          : 'max-w-7xl'

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.12),_transparent_32%),linear-gradient(180deg,_#f8fafc_0%,_#f8fafc_100%)] px-4 py-6 sm:px-6 sm:py-10">
      <div className={cn('mx-auto', widthClass, className)}>{children}</div>
    </div>
  )
}

export function HeroCard({
  eyebrow = undefined,
  title,
  subtitle = undefined,
  description = undefined,
  action = undefined,
  children = undefined,
  className = '',
  centered = false,
  showLogo = false,
  logoSize = 'md',
  titleClassName = '',
  subtitleClassName = '',
}) {
  return (
    <div
      className={cn(
        'overflow-hidden rounded-[28px] border border-violet-200/70 bg-white shadow-[0_18px_48px_rgba(76,29,149,0.10)]',
        className,
      )}
    >
      <div className="h-3 bg-gradient-to-r from-violet-700 via-violet-500 to-fuchsia-500" />
      <div className="space-y-5 px-6 py-6 sm:px-8 sm:py-8">
        {centered ? (
          <div className="relative">
            {action && <div className="absolute right-0 top-0 z-10">{action}</div>}
            <div className={cn('w-full space-y-3 text-center', action && 'sm:pr-32')}>
            {showLogo && <AppLogo size={logoSize} centered />}
            {eyebrow && (
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-600">
                {eyebrow}
              </p>
            )}
            <h1
              className={cn(
                'text-2xl font-semibold tracking-tight sm:text-3xl',
                centered ? 'text-violet-700' : 'text-slate-950',
                titleClassName,
              )}
            >
              {title}
            </h1>
            {subtitle && (
              <p
                className={cn(
                  centered
                    ? 'mx-auto w-full max-w-4xl px-2 text-lg font-medium leading-8 text-slate-600 sm:px-8 sm:text-xl'
                    : 'max-w-3xl text-base font-medium leading-7 text-slate-700',
                  subtitleClassName,
                )}
              >
                {subtitle}
              </p>
            )}
            {description && (
              <p
                className={cn(
                  'text-sm leading-6 text-slate-600',
                  centered ? 'mx-auto max-w-2xl' : 'max-w-3xl',
                )}
              >
                {description}
              </p>
            )}
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              {showLogo && <AppLogo size={logoSize} centered={false} className="mb-2" />}
              {eyebrow && (
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-600">
                  {eyebrow}
                </p>
              )}
              <h1
                className={cn(
                  'text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl',
                  titleClassName,
                )}
              >
                {title}
              </h1>
              {subtitle && (
                <p
                  className={cn(
                    'max-w-3xl text-base font-medium leading-7 text-slate-700',
                    subtitleClassName,
                  )}
                >
                  {subtitle}
                </p>
              )}
              {description && (
                <p className="max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
              )}
            </div>
            {action}
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

export function SurfaceCard({ children, className = '' }) {
  return (
    <div
      className={cn(
        'rounded-[24px] border border-slate-200/90 bg-white p-5 shadow-[0_16px_40px_rgba(15,23,42,0.06)] sm:p-6',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function SectionHeader({ eyebrow, title, description, action, className = '' }) {
  return (
    <div className={cn('flex flex-wrap items-start justify-between gap-4', className)}>
      <div className="space-y-1.5">
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">{eyebrow}</p>
        )}
        <h2 className="text-xl font-semibold text-slate-950">{title}</h2>
        {description && <p className="max-w-2xl text-sm text-slate-600">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function StatCard({ label, value, help, tone = 'neutral' }) {
  const toneClass =
    tone === 'brand'
      ? 'border-violet-200 bg-violet-50/70'
      : tone === 'success'
        ? 'border-emerald-200 bg-emerald-50/70'
        : 'border-slate-200 bg-slate-50/80'

  return (
    <div className={cn('rounded-2xl border p-4', toneClass)}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      {help && <p className="mt-1 text-sm text-slate-600">{help}</p>}
    </div>
  )
}

export function TextInput({ className = '', ...props }) {
  return <input {...props} className={cn(inputClassName, className)} />
}

export function TextAreaInput({ className = '', ...props }) {
  return <textarea {...props} className={cn(inputClassName, 'min-h-[120px] resize-y', className)} />
}

export function SelectInput({ className = '', children, ...props }) {
  return (
    <select {...props} className={cn(inputClassName, className)}>
      {children}
    </select>
  )
}

export function FormLabel({ label, hint, children, className = '', htmlFor }) {
  const autoId = useId()
  const fieldId = htmlFor || autoId
  const control =
    isValidElement(children) && !children.props.id
      ? cloneElement(children, { id: fieldId })
      : children

  return (
    <label htmlFor={fieldId} className={cn('flex flex-col gap-2 text-sm', className)}>
      <div className="space-y-0.5">
        <span className="font-medium text-slate-800">{label}</span>
        {hint && <p className="text-xs text-slate-500">{hint}</p>}
      </div>
      {control}
    </label>
  )
}

export function confirmAction(message) {
  return window.confirm(message)
}

export function PrimaryButton({ className = '', tone = 'brand', children, ...props }) {
  const toneClass =
    tone === 'success'
      ? 'bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-100'
      : tone === 'dark'
        ? 'bg-slate-900 hover:bg-slate-950 focus:ring-slate-200'
        : 'bg-violet-600 hover:bg-violet-700 focus:ring-violet-100'

  return (
    <button
      {...props}
      className={cn(
        'inline-flex items-center justify-center rounded-2xl px-4 py-3 text-sm font-medium text-white shadow-sm transition focus:outline-none focus:ring-4 disabled:cursor-not-allowed disabled:opacity-60',
        toneClass,
        className,
      )}
    >
      {children}
    </button>
  )
}

export function SecondaryButton({ className = '', children, ...props }) {
  return (
    <button
      {...props}
      className={cn(
        'inline-flex items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-slate-100 disabled:cursor-not-allowed disabled:opacity-60',
        className,
      )}
    >
      {children}
    </button>
  )
}

export function Pill({ children, tone = 'neutral', className = '' }) {
  const toneClass =
    tone === 'brand'
      ? 'bg-violet-100 text-violet-700'
      : tone === 'success'
        ? 'bg-emerald-100 text-emerald-700'
        : 'bg-slate-100 text-slate-600'

  return (
    <span className={cn('inline-flex items-center rounded-full px-3 py-1 text-xs font-medium', toneClass, className)}>
      {children}
    </span>
  )
}

export function StatusMessage({ children, tone = 'error', className = '' }) {
  const toneClass =
    tone === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : 'border-rose-200 bg-rose-50 text-rose-700'

  return (
    <div className={cn('rounded-2xl border px-4 py-3 text-sm', toneClass, className)}>
      {children}
    </div>
  )
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="rounded-[24px] border border-dashed border-slate-300 bg-white/70 px-6 py-10 text-center shadow-sm">
      <h3 className="text-lg font-medium text-slate-900">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm text-slate-600">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function TabLink({ to, active, children }) {
  return (
    <Link
      to={to}
      className={cn(
        'rounded-full px-4 py-2 text-sm font-medium transition',
        active
          ? 'bg-violet-600 text-white shadow-sm'
          : 'bg-white text-slate-600 hover:bg-violet-50 hover:text-violet-700',
      )}
    >
      {children}
    </Link>
  )
}
