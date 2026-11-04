import { useState } from 'react'
import {
  Calendar,
  ChevronDown,
  ChevronRight,
  Link2,
  ListChecks,
  Target,
  User,
} from 'lucide-react'
import type { KnowledgeItem } from '../lib/types'
import { EvidenceList } from './EvidenceList'
import {
  EvidenceBadge,
  ReviewBadge,
  SeverityBadge,
  TaskStatusBadge,
  TypeBadge,
} from './ui'

function DetailRow({ label, value, icon }: { label: string; value: string | null | undefined; icon?: React.ReactNode }) {
  if (value == null || value === '') return null
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="mt-0.5 shrink-0 text-ink-500">{icon}</span>
      <span className="shrink-0 w-32 text-ink-400">{label}</span>
      <span className="text-ink-200">{value}</span>
    </div>
  )
}

function DetailsPanel({ item }: { item: KnowledgeItem }) {
  const d = item.details ?? {}
  switch (item.type) {
    case 'decision':
      return (
        <div className="space-y-1.5">
          <DetailRow label="Reason" value={d.reason as string} />
          <DetailRow
            label="Alternatives"
            value={(d.alternatives as string[] | undefined)?.length
              ? (d.alternatives as string[]).join(', ')
              : undefined}
          />
          <DetailRow label="Decided on" value={d.decided_on as string} icon={<Calendar size={13} />} />
          <DetailRow
            label="Affects"
            value={(d.affected as string[] | undefined)?.length
              ? (d.affected as string[]).join(', ')
              : undefined}
            icon={<Target size={13} />}
          />
        </div>
      )
    case 'task':
      return (
        <div className="space-y-1.5">
          <DetailRow label="Description" value={d.description as string} />
          <DetailRow label="Assignee" value={item.assignee} icon={<User size={13} />} />
          <DetailRow label="Due date" value={item.due_date} icon={<Calendar size={13} />} />
          <DetailRow
            label="Dependencies"
            value={item.dependencies.length ? item.dependencies.join(', ') : undefined}
            icon={<ListChecks size={13} />}
          />
        </div>
      )
    case 'event':
      return (
        <div className="space-y-1.5">
          <DetailRow label="Date" value={d.event_date as string} icon={<Calendar size={13} />} />
          <DetailRow label="Description" value={d.description as string} />
        </div>
      )
    case 'risk':
      return (
        <div className="space-y-1.5">
          <DetailRow label="Description" value={d.description as string} />
          <DetailRow label="Risk status" value={d.status as string} />
          {d.mentioned === false && (
            <div className="text-xs text-amber-300/80">
              Model-inferred risk — the source does not state it explicitly.
            </div>
          )}
        </div>
      )
    case 'question':
      return (
        <div className="space-y-1.5">
          <DetailRow label="Context" value={d.context as string} />
        </div>
      )
    case 'entity':
      return (
        <div className="space-y-1.5">
          <DetailRow label="Kind" value={d.entity_kind as string} />
        </div>
      )
    default:
      return null
  }
}

export function KnowledgeItemCard({
  item,
  onOpen,
  defaultExpanded = false,
}: {
  item: KnowledgeItem
  onOpen?: (item: KnowledgeItem) => void
  defaultExpanded?: boolean
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const hasDetails =
    item.type === 'decision' ||
    item.type === 'task' ||
    item.type === 'event' ||
    item.type === 'risk' ||
    item.type === 'question' ||
    item.type === 'entity'

  return (
    <div className="rounded-xl border border-navy-700 bg-navy-900 p-4 transition hover:border-navy-600">
      <div className="flex flex-wrap items-center gap-2">
        <TypeBadge type={item.type} />
        {item.type === 'task' && item.task_status && <TaskStatusBadge status={item.task_status} />}
        {item.type === 'risk' && item.severity && <SeverityBadge severity={item.severity} />}
        <EvidenceBadge status={item.evidence_status} />
        <ReviewBadge status={item.review_status} />
        {item.reviewed_by && (
          <span className="ml-auto text-[11px] text-ink-500">
            reviewed by {item.reviewed_by}
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={() => (onOpen ? onOpen(item) : setExpanded((v) => !v))}
        className="mt-2 block text-left"
      >
        <span className="text-sm font-semibold text-ink-50 hover:text-brand-300">
          {item.title}
        </span>
      </button>

      {item.summary && item.summary !== item.title && (
        <p className="mt-1 text-xs leading-relaxed text-ink-400">{item.summary}</p>
      )}

      {expanded && (
        <div className="mt-3 space-y-4 border-t border-navy-700 pt-3">
          {hasDetails && (
            <div>
              <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                Details
              </div>
              <DetailsPanel item={item} />
            </div>
          )}
          {item.relationships.length > 0 && (
            <div>
              <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                Relationships
              </div>
              <div className="flex flex-wrap gap-1.5">
                {item.relationships.map((r, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 rounded-md border border-navy-600 bg-navy-850 px-2 py-0.5 text-[11px] text-ink-300"
                  >
                    <Link2 size={11} className="text-brand-300" />
                    {r.type.replace('_', ' ')} → {r.target_title ?? `#${r.target_id}`}
                  </span>
                ))}
              </div>
            </div>
          )}
          <div>
            <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
              Evidence ({item.evidence.length})
            </div>
            <EvidenceList evidence={item.evidence} />
          </div>
        </div>
      )}

      {!onOpen && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-ink-400 hover:text-ink-200"
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      )}
    </div>
  )
}