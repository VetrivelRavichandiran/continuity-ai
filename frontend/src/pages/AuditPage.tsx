import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { api, formatDateTime } from '../lib/api'
import type { AuditEntry } from '../lib/types'
import { Badge, Card, EmptyState, ErrorNote, PageHeader, Spinner } from '../components/ui'

const ACTION_TONES: Record<string, string> = {
  project_created: 'bg-brand-500/15 text-brand-300 border-brand-500/30',
  document_uploaded: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  document_processed: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
  document_deleted: 'bg-red-500/15 text-red-300 border-red-500/30',
  knowledge_created: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
  record_edited: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  record_approved: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
  record_rejected: 'bg-red-500/15 text-red-300 border-red-500/30',
  record_flagged: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
  conflict_resolved: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
  handover_generated: 'bg-brand-500/15 text-brand-300 border-brand-500/30',
}

export default function AuditPage() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const [entries, setEntries] = useState<AuditEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .audit(pid, 200)
      .then(setEntries)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load audit log'))
  }, [pid])

  if (error) return <ErrorNote message={error} />
  if (!entries) return <Spinner label="Loading audit log…" />

  return (
    <div>
      <PageHeader
        title="Audit log"
        subtitle="Every action on this project is recorded: uploads, processing, edits, reviews, conflict resolutions and handover generation."
      />

      {entries.length === 0 ? (
        <EmptyState title="No audit entries yet" />
      ) : (
        <Card className="divide-y divide-navy-800">
          {entries.map((e) => (
            <div key={e.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
              <Badge tone={ACTION_TONES[e.action] ?? undefined}>
                {e.action.replace(/_/g, ' ')}
              </Badge>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm text-ink-200">
                  {e.entity_title ?? e.entity_type ?? '—'}
                </div>
                {e.detail && (
                  <div className="truncate text-xs text-ink-500">{e.detail}</div>
                )}
              </div>
              {e.reviewer && (
                <span className="inline-flex items-center gap-1 text-xs text-ink-400">
                  <ShieldCheck size={12} className="text-teal-300" />
                  {e.reviewer}
                </span>
              )}
              <span className="text-[11px] whitespace-nowrap text-ink-500">
                {formatDateTime(e.created_at)}
              </span>
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}