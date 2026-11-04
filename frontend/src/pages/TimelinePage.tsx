import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Calendar, GitBranch } from 'lucide-react'
import { api } from '../lib/api'
import type { TimelineEntry } from '../lib/types'
import { EvidenceList } from '../components/EvidenceList'
import { EmptyState, ErrorNote, PageHeader, Spinner } from '../components/ui'

export default function TimelinePage() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const [entries, setEntries] = useState<TimelineEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useState<number | null>(null)

  useEffect(() => {
    api
      .timeline(pid)
      .then(setEntries)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load timeline'))
  }, [pid])

  if (error) return <ErrorNote message={error} />
  if (!entries) return <Spinner label="Loading timeline…" />

  return (
    <div>
      <PageHeader
        title="Timeline"
        subtitle="Dated events and decisions in chronological order. Entries without a date appear last."
      />

      {entries.length === 0 ? (
        <EmptyState title="No dated events or decisions yet" hint="Upload documents containing dated events or decisions to build the timeline." />
      ) : (
        <div className="relative ml-3 border-l border-navy-700 pl-8">
          {entries.map((e) => (
            <div key={`${e.type}-${e.id}`} className="relative mb-6">
              <span
                className={`absolute top-1 -left-[41px] flex h-6 w-6 items-center justify-center rounded-full border-2 border-navy-950 ${
                  e.type === 'event'
                    ? 'bg-purple-500/30 text-purple-300'
                    : 'bg-brand-500/30 text-brand-300'
                }`}
              >
                {e.type === 'event' ? <Calendar size={12} /> : <GitBranch size={12} />}
              </span>

              <div className="rounded-xl border border-navy-700 bg-navy-900 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      e.type === 'event'
                        ? 'bg-purple-500/15 text-purple-300'
                        : 'bg-brand-500/15 text-brand-300'
                    }`}
                  >
                    {e.type}
                  </span>
                  <span className="text-xs font-medium text-ink-500">
                    {e.date ?? 'Undated'}
                  </span>
                </div>
                <div className="mt-1.5 text-sm font-semibold text-ink-50">{e.title}</div>
                {e.description && e.description !== e.title && (
                  <p className="mt-1 text-xs leading-relaxed text-ink-400">{e.description}</p>
                )}
                {openId === e.id && (
                  <div className="mt-3">
                    <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                      Evidence
                    </div>
                    <EvidenceList evidence={e.evidence} />
                  </div>
                )}
                {e.evidence.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setOpenId(openId === e.id ? null : e.id)}
                    className="mt-2 text-xs font-medium text-brand-300 hover:text-brand-400"
                  >
                    {openId === e.id ? 'Hide evidence' : `Show evidence (${e.evidence.length})`}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}