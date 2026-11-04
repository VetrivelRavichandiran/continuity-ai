import { useEffect, useState } from 'react'
import { Check, Flag, Pencil, ShieldCheck, X } from 'lucide-react'
import { api } from '../lib/api'
import type { KnowledgeItem, Severity, TaskStatus } from '../lib/types'
import { EvidenceList } from './EvidenceList'
import {
  Button,
  EvidenceBadge,
  Field,
  inputCls,
  Modal,
  ReviewBadge,
  SeverityBadge,
  TaskStatusBadge,
  TypeBadge,
} from './ui'

const TASK_STATUSES: TaskStatus[] = ['pending', 'in_progress', 'completed', 'blocked']
const SEVERITIES: Severity[] = ['low', 'medium', 'high', 'critical']

export function KnowledgeDetailModal({
  item: initial,
  onClose,
  onChanged,
}: {
  item: KnowledgeItem
  onClose: () => void
  onChanged?: (item: KnowledgeItem) => void
}) {
  const [item, setItem] = useState<KnowledgeItem>(initial)
  const [editing, setEditing] = useState(false)
  const [reviewing, setReviewing] = useState(false)
  const [note, setNote] = useState('')
  const [reviewer, setReviewer] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // edit form state
  const [fTitle, setFTitle] = useState('')
  const [fSummary, setFSummary] = useState('')
  const [fTaskStatus, setFTaskStatus] = useState('')
  const [fSeverity, setFSeverity] = useState('')
  const [fAssignee, setFAssignee] = useState('')
  const [fDueDate, setFDueDate] = useState('')

  useEffect(() => {
    setItem(initial)
    setFTitle(initial.title)
    setFSummary(initial.summary ?? '')
    setFTaskStatus(initial.task_status ?? '')
    setFSeverity(initial.severity ?? '')
    setFAssignee(initial.assignee ?? '')
    setFDueDate(initial.due_date ?? '')
    setError(null)
  }, [initial])

  const saveEdit = async () => {
    setBusy(true)
    setError(null)
    try {
      const body: Record<string, unknown> = {}
      if (fTitle.trim() && fTitle !== item.title) body.title = fTitle.trim()
      if (fSummary !== (item.summary ?? '')) body.summary = fSummary || null
      if (item.type === 'task') {
        if (fTaskStatus !== (item.task_status ?? '')) body.task_status = fTaskStatus || null
        if (fAssignee !== (item.assignee ?? '')) body.assignee = fAssignee || null
        if (fDueDate !== (item.due_date ?? '')) body.due_date = fDueDate || null
      }
      if (item.type === 'risk' && fSeverity !== (item.severity ?? '')) {
        body.severity = fSeverity || null
      }
      if (Object.keys(body).length === 0) {
        setEditing(false)
        return
      }
      const updated = await api.patchKnowledge(item.id, body)
      setItem(updated)
      setEditing(false)
      onChanged?.(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save changes')
    } finally {
      setBusy(false)
    }
  }

  const doReview = async (action: 'approve' | 'reject' | 'flag' | 'resolve_conflict') => {
    setBusy(true)
    setError(null)
    try {
      const updated = await api.reviewKnowledge(item.id, {
        action,
        reviewer: reviewer.trim() || undefined,
        note: note.trim() || undefined,
      })
      setItem(updated)
      setReviewing(false)
      setNote('')
      onChanged?.(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Review failed')
    } finally {
      setBusy(false)
    }
  }

  const d = item.details ?? {}

  return (
    <Modal open onClose={onClose} title={<span className="flex items-center gap-2"><TypeBadge type={item.type} /> {item.title}</span>} wide>
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          {item.type === 'task' && item.task_status && <TaskStatusBadge status={item.task_status} />}
          {item.type === 'risk' && item.severity && <SeverityBadge severity={item.severity} />}
          <EvidenceBadge status={item.evidence_status} />
          <ReviewBadge status={item.review_status} />
          {item.reviewed_by && (
            <span className="text-xs text-ink-500">
              {item.reviewed_by} · {item.reviewed_at}
            </span>
          )}
        </div>

        {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}

        {/* summary */}
        {item.summary && (
          <div className="text-sm leading-relaxed text-ink-200">{item.summary}</div>
        )}

        {/* type-specific details */}
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {item.type === 'decision' && (
            <>
              {d.reason && <Info label="Reason" value={String(d.reason)} />}
              {(d.alternatives as string[] | undefined)?.length ? (
                <Info label="Alternatives" value={(d.alternatives as string[]).join(', ')} />
              ) : null}
              {d.decided_on && <Info label="Decided on" value={String(d.decided_on)} />}
              {(d.affected as string[] | undefined)?.length ? (
                <Info label="Affects" value={(d.affected as string[]).join(', ')} />
              ) : null}
            </>
          )}
          {item.type === 'task' && (
            <>
              {d.description && <Info label="Description" value={String(d.description)} />}
              <Info label="Assignee" value={item.assignee} />
              <Info label="Due date" value={item.due_date} />
              {item.dependencies.length > 0 && (
                <Info label="Dependencies" value={item.dependencies.join(', ')} />
              )}
            </>
          )}
          {item.type === 'event' && (
            <>
              <Info label="Date" value={d.event_date as string} />
              {d.description && <Info label="Description" value={String(d.description)} />}
            </>
          )}
          {item.type === 'risk' && (
            <>
              {d.description && <Info label="Description" value={String(d.description)} />}
              <Info label="Risk status" value={d.status as string} />
              {d.mentioned === false && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300 sm:col-span-2">
                  Model-inferred risk — the source does not state it explicitly.
                </div>
              )}
            </>
          )}
          {item.type === 'question' && Boolean(d.context) && (
            <Info label="Context" value={String(d.context)} />
          )}
          {item.type === 'entity' && (
            <Info label="Kind" value={d.entity_kind as string} />
          )}
        </div>

        {/* relationships */}
        {item.relationships.length > 0 && (
          <div>
            <SectionLabel>Relationships</SectionLabel>
            <div className="flex flex-wrap gap-1.5">
              {item.relationships.map((r, i) => (
                <span
                  key={i}
                  className="rounded-md border border-navy-600 bg-navy-850 px-2 py-1 text-xs text-ink-300"
                >
                  <span className="text-brand-300">{r.type.replace('_', ' ')}</span> →{' '}
                  {r.target_title ?? `#${r.target_id}`}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* evidence */}
        <div>
          <SectionLabel>Evidence ({item.evidence.length})</SectionLabel>
          <EvidenceList evidence={item.evidence} max={4} />
        </div>

        {/* edit form */}
        {editing && (
          <div className="space-y-3 rounded-xl border border-brand-500/30 bg-navy-850 p-4">
            <div className="text-sm font-semibold text-ink-100">Edit record</div>
            <Field label="Title">
              <input className={inputCls} value={fTitle} onChange={(e) => setFTitle(e.target.value)} />
            </Field>
            <Field label="Summary">
              <textarea
                className={`${inputCls} min-h-20 resize-y`}
                value={fSummary}
                onChange={(e) => setFSummary(e.target.value)}
              />
            </Field>
            {item.type === 'task' && (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Field label="Task status">
                  <select className={inputCls} value={fTaskStatus} onChange={(e) => setFTaskStatus(e.target.value)}>
                    <option value="">—</option>
                    {TASK_STATUSES.map((s) => (
                      <option key={s} value={s}>{s.replace('_', ' ')}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Assignee">
                  <input className={inputCls} value={fAssignee} onChange={(e) => setFAssignee(e.target.value)} />
                </Field>
                <Field label="Due date">
                  <input className={inputCls} type="date" value={fDueDate} onChange={(e) => setFDueDate(e.target.value)} />
                </Field>
              </div>
            )}
            {item.type === 'risk' && (
              <Field label="Severity">
                <select className={inputCls} value={fSeverity} onChange={(e) => setFSeverity(e.target.value)}>
                  <option value="">—</option>
                  {SEVERITIES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </Field>
            )}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
              <Button onClick={saveEdit} disabled={busy}>
                <Check size={15} /> Save changes
              </Button>
            </div>
          </div>
        )}

        {/* review form */}
        {reviewing && (
          <div className="space-y-3 rounded-xl border border-brand-500/30 bg-navy-850 p-4">
            <div className="text-sm font-semibold text-ink-100">Review this record</div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Reviewer name">
                <input className={inputCls} placeholder="e.g. Demo Reviewer" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
              </Field>
              <Field label="Note">
                <input
                  className={inputCls}
                  placeholder={item.evidence_status === 'conflicting' ? 'Required: which side was kept' : 'Optional note'}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </Field>
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="ghost" onClick={() => { setReviewing(false); setNote('') }}>Cancel</Button>
              <Button variant="danger" onClick={() => doReview('reject')} disabled={busy}>
                <X size={15} /> Reject
              </Button>
              <Button variant="secondary" onClick={() => doReview('flag')} disabled={busy}>
                <Flag size={15} /> Flag
              </Button>
              {item.evidence_status === 'conflicting' && (
                <Button variant="secondary" onClick={() => doReview('resolve_conflict')} disabled={busy || !note.trim()}>
                  <ShieldCheck size={15} /> Resolve conflict
                </Button>
              )}
              <Button onClick={() => doReview('approve')} disabled={busy}>
                <Check size={15} /> Approve
              </Button>
            </div>
          </div>
        )}

        {/* actions */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-navy-700 pt-4">
          <span className="text-[11px] text-ink-500">
            ID {item.id} · created {item.created_at} · updated {item.updated_at}
          </span>
          <div className="flex gap-2">
            {!editing && !reviewing && (
              <>
                <Button variant="secondary" onClick={() => setEditing(true)}>
                  <Pencil size={14} /> Edit
                </Button>
                <Button variant="primary" onClick={() => setReviewing(true)}>
                  <ShieldCheck size={14} /> Review
                </Button>
              </>
            )}
            <Button variant="ghost" onClick={onClose}>Close</Button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

function Info({ label, value }: { label: string; value: string | null | undefined }) {
  if (value == null || value === '') return null
  return (
    <div className="rounded-lg border border-navy-700 bg-navy-850 px-3 py-2">
      <div className="text-[11px] font-medium tracking-wide text-ink-500 uppercase">{label}</div>
      <div className="mt-0.5 text-sm text-ink-200">{value}</div>
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">{children}</div>
  )
}