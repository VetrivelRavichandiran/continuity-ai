import { useEffect, type ReactNode } from 'react'
import { X, Loader2, Inbox } from 'lucide-react'
import type { EvidenceStatus, ReviewStatus, Severity, TaskStatus } from '../lib/types'

// ---------------------------------------------------------------------------
// badges
// ---------------------------------------------------------------------------

const REVIEW_STYLES: Record<ReviewStatus, string> = {
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  approved: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
  rejected: 'bg-red-500/15 text-red-300 border-red-500/30',
  flagged: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
}

const EVIDENCE_STYLES: Record<EvidenceStatus, string> = {
  supported: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
  inferred: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  conflicting: 'bg-red-500/15 text-red-300 border-red-500/30',
  unverified: 'bg-ink-500/15 text-ink-300 border-ink-500/30',
}

const SEVERITY_STYLES: Record<Severity, string> = {
  low: 'bg-ink-500/15 text-ink-300 border-ink-500/30',
  medium: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  high: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
  critical: 'bg-red-500/15 text-red-300 border-red-500/30',
}

const TASK_STATUS_STYLES: Record<TaskStatus, string> = {
  completed: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
  in_progress: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  blocked: 'bg-red-500/15 text-red-300 border-red-500/30',
}

const TYPE_STYLES: Record<string, string> = {
  decision: 'bg-brand-500/15 text-brand-300 border-brand-500/30',
  task: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  event: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
  risk: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
  question: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  entity: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
}

export function Badge({
  children,
  className = '',
  tone,
}: {
  children: ReactNode
  className?: string
  tone?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${tone ?? 'bg-ink-500/15 text-ink-300 border-ink-500/30'} ${className}`}
    >
      {children}
    </span>
  )
}

export const ReviewBadge = ({ status }: { status: ReviewStatus }) => (
  <Badge tone={REVIEW_STYLES[status]}>{status}</Badge>
)
export const EvidenceBadge = ({ status }: { status: EvidenceStatus }) => (
  <Badge tone={EVIDENCE_STYLES[status]}>{status}</Badge>
)
export const SeverityBadge = ({ severity }: { severity: Severity }) => (
  <Badge tone={SEVERITY_STYLES[severity]}>{severity.toUpperCase()}</Badge>
)
export const TaskStatusBadge = ({ status }: { status: TaskStatus }) => (
  <Badge tone={TASK_STATUS_STYLES[status]}>{status.replace('_', ' ')}</Badge>
)
export const TypeBadge = ({ type }: { type: string }) => (
  <Badge tone={TYPE_STYLES[type] ?? TYPE_STYLES.entity}>{type}</Badge>
)

// ---------------------------------------------------------------------------
// layout primitives
// ---------------------------------------------------------------------------

export function Card({
  children,
  className = '',
  onClick,
}: {
  children: ReactNode
  className?: string
  onClick?: () => void
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-xl border border-navy-700 bg-navy-900 ${onClick ? 'cursor-pointer transition hover:border-navy-600' : ''} ${className}`}
    >
      {children}
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-50">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

export function StatCard({
  label,
  value,
  icon,
  tone = 'text-brand-300',
  hint,
}: {
  label: string
  value: ReactNode
  icon?: ReactNode
  tone?: string
  hint?: string
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium tracking-wide text-ink-400 uppercase">{label}</span>
        {icon && <span className={tone}>{icon}</span>}
      </div>
      <div className="mt-2 text-2xl font-semibold text-ink-50">{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-500">{hint}</div>}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// buttons
// ---------------------------------------------------------------------------

type BtnVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const BTN_STYLES: Record<BtnVariant, string> = {
  primary:
    'bg-brand-500 text-white hover:bg-brand-400 disabled:bg-brand-600/60 border border-transparent',
  secondary:
    'bg-navy-800 text-ink-100 hover:bg-navy-700 border border-navy-600 disabled:opacity-50',
  ghost: 'bg-transparent text-ink-300 hover:bg-navy-800 border border-transparent disabled:opacity-50',
  danger: 'bg-red-500/15 text-red-300 hover:bg-red-500/25 border border-red-500/30 disabled:opacity-50',
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  disabled,
  type = 'button',
  className = '',
  title,
}: {
  children: ReactNode
  onClick?: () => void
  variant?: BtnVariant
  disabled?: boolean
  type?: 'button' | 'submit'
  className?: string
  title?: string
}) {
  return (
    <button
      type={type}
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed ${BTN_STYLES[variant]} ${className}`}
    >
      {children}
    </button>
  )
}

export function IconButton({
  children,
  onClick,
  title,
  className = '',
  danger,
  disabled,
}: {
  children: ReactNode
  onClick?: () => void
  title?: string
  className?: string
  danger?: boolean
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-ink-400 transition hover:bg-navy-800 hover:text-ink-100 disabled:cursor-not-allowed disabled:opacity-40 ${danger ? 'hover:text-red-300' : ''} ${className}`}
    >
      {children}
    </button>
  )
}

// ---------------------------------------------------------------------------
// modal
// ---------------------------------------------------------------------------

export function Modal({
  open,
  onClose,
  title,
  children,
  wide,
}: {
  open: boolean
  onClose: () => void
  title: ReactNode
  children: ReactNode
  wide?: boolean
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm sm:p-8"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className={`animate-fade-in my-auto w-full ${wide ? 'max-w-3xl' : 'max-w-xl'} rounded-2xl border border-navy-700 bg-navy-900 shadow-2xl`}
      >
        <div className="flex items-center justify-between border-b border-navy-700 px-5 py-4">
          <h3 className="text-base font-semibold text-ink-50">{title}</h3>
          <IconButton title="Close" onClick={onClose}>
            <X size={18} />
          </IconButton>
        </div>
        <div className="max-h-[75vh] overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// feedback
// ---------------------------------------------------------------------------

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-ink-400">
      <Loader2 size={20} className="animate-spin" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  )
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string
  hint?: string
  action?: ReactNode
}) {
  return (
    <Card className="flex flex-col items-center justify-center gap-2 p-12 text-center">
      <Inbox size={32} className="text-ink-500" />
      <div className="text-sm font-medium text-ink-200">{title}</div>
      {hint && <div className="max-w-md text-xs text-ink-500">{hint}</div>}
      {action && <div className="mt-3">{action}</div>}
    </Card>
  )
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
      {message}
    </div>
  )
}

// ---------------------------------------------------------------------------
// forms
// ---------------------------------------------------------------------------

export function Field({
  label,
  children,
  hint,
}: {
  label: string
  children: ReactNode
  hint?: string
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium tracking-wide text-ink-400 uppercase">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-ink-500">{hint}</span>}
    </label>
  )
}

export const inputCls =
  'w-full rounded-lg border border-navy-600 bg-navy-850 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-500 focus:border-brand-400 focus:outline-none'

// ---------------------------------------------------------------------------
// progress
// ---------------------------------------------------------------------------

export function ProgressRing({
  percent,
  size = 120,
  stroke = 10,
  label,
  sub,
}: {
  percent: number
  size?: number
  stroke?: number
  label?: string
  sub?: string
}) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const off = c * (1 - Math.min(100, Math.max(0, percent)) / 100)
  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-navy-700)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--color-teal-500)"
          strokeWidth={stroke}
          strokeDasharray={c}
          strokeDashoffset={off}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-2xl font-semibold text-ink-50">{label ?? `${Math.round(percent)}%`}</div>
        {sub && <div className="text-[11px] text-ink-400">{sub}</div>}
      </div>
    </div>
  )
}

export function ProgressBar({
  segments,
}: {
  segments: { value: number; color: string }[]
}) {
  const total = segments.reduce((a, s) => a + s.value, 0)
  return (
    <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-navy-700">
      {total > 0 &&
        segments.map((s, i) => (
          <div
            key={i}
            style={{ width: `${(s.value / total) * 100}%`, background: s.color }}
            className="h-full transition-all"
          />
        ))}
    </div>
  )
}