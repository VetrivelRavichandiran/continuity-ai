import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle, Check, ShieldCheck } from 'lucide-react'
import { api } from '../lib/api'
import type { Conflict } from '../lib/types'
import { EvidenceList } from '../components/EvidenceList'
import {
  Button,
  Card,
  EmptyState,
  ErrorNote,
  Field,
  inputCls,
  Modal,
  PageHeader,
  Spinner,
  TypeBadge,
} from '../components/ui'

export default function ConflictsPage() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const [conflicts, setConflicts] = useState<Conflict[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [resolving, setResolving] = useState<{ conflict: Conflict; keep: number } | null>(null)

  const load = useCallback(() => {
    setError(null)
    api
      .conflicts(pid)
      .then(setConflicts)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load conflicts'))
  }, [pid])

  useEffect(load, [load])

  if (error) return <ErrorNote message={error} />
  if (!conflicts) return <Spinner label="Loading conflicts…" />

  return (
    <div>
      <PageHeader
        title="Conflicts"
        subtitle="Records where two sources disagree on the same topic. Both items are marked 'conflicting' until a reviewer resolves which side is kept."
      />

      {conflicts.length === 0 ? (
        <EmptyState
          title="No conflicts detected"
          hint="When two documents disagree on the same topic (e.g. one says work is complete, the other says it is pending), the conflict appears here."
        />
      ) : (
        <div className="space-y-4">
          {conflicts.map((c) => (
            <Card key={c.id} className="overflow-hidden">
              <div className="flex items-center gap-2 border-b border-navy-700 bg-red-500/5 px-4 py-3">
                <AlertTriangle size={16} className="text-red-300" />
                <span className="text-sm font-semibold text-ink-50">{c.topic}</span>
                <span className="ml-auto text-[11px] text-ink-500">conflict #{c.id}</span>
              </div>
              <div className="grid grid-cols-1 gap-px bg-navy-700 md:grid-cols-2">
                {c.items.map((item) => (
                  <div key={item.id} className="bg-navy-900 p-4">
                    <div className="flex items-center gap-2">
                      <TypeBadge type={item.type ?? 'unknown'} />
                      <span className="text-[11px] text-ink-500">record #{item.id}</span>
                    </div>
                    <div className="mt-2 text-sm font-medium text-ink-100">{item.title}</div>
                    <div className="mt-3">
                      <EvidenceList evidence={item.evidence} max={2} />
                    </div>
                    <div className="mt-3">
                      <Button
                        variant="secondary"
                        onClick={() => setResolving({ conflict: c, keep: item.id })}
                      >
                        <ShieldCheck size={14} /> Keep this side
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}

      {resolving && (
        <ResolveModal
          conflict={resolving.conflict}
          keepId={resolving.keep}
          onClose={() => setResolving(null)}
          onDone={() => {
            setResolving(null)
            load()
          }}
        />
      )}
    </div>
  )
}

function ResolveModal({
  conflict,
  keepId,
  onClose,
  onDone,
}: {
  conflict: Conflict
  keepId: number
  onClose: () => void
  onDone: () => void
}) {
  const kept = conflict.items.find((i) => i.id === keepId)
  const other = conflict.items.find((i) => i.id !== keepId)
  const [note, setNote] = useState('')
  const [reviewer, setReviewer] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    if (!note.trim()) {
      setError('A note explaining which side was kept is required.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await api.reviewKnowledge(keepId, {
        action: 'resolve_conflict',
        reviewer: reviewer.trim() || undefined,
        note: note.trim(),
      })
      onDone()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to resolve conflict')
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Resolve conflict" wide>
      <div className="space-y-4">
        <div className="rounded-lg border border-teal-500/30 bg-teal-500/10 px-4 py-3 text-sm text-teal-300">
          Keeping: <b>{kept?.title}</b>
        </div>
        {other && (
          <div className="rounded-lg border border-navy-700 bg-navy-850 px-4 py-3 text-sm text-ink-400">
            Discarding: <b className="text-ink-200">{other.title}</b>
          </div>
        )}
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Reviewer">
            <input
              className={inputCls}
              placeholder="e.g. Demo Reviewer"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
            />
          </Field>
          <Field label="Note (required)">
            <input
              className={inputCls}
              placeholder="Which side was kept and why"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={busy || !note.trim()}>
            <Check size={15} /> Resolve conflict
          </Button>
        </div>
      </div>
    </Modal>
  )
}