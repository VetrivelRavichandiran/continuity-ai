import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api } from '../lib/api'
import type { KnowledgeItem, KnowledgeType, ReviewStatus, TaskStatus } from '../lib/types'
import { KnowledgeItemCard } from '../components/KnowledgeItemCard'
import { KnowledgeDetailModal } from '../components/KnowledgeDetailModal'
import { EmptyState, ErrorNote, inputCls, PageHeader, Spinner } from '../components/ui'

const TYPES: (KnowledgeType | 'all')[] = [
  'all',
  'decision',
  'task',
  'event',
  'risk',
  'question',
  'entity',
]

export default function KnowledgePage() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const [params, setParams] = useSearchParams()

  const type = (params.get('type') ?? 'all') as KnowledgeType | 'all'
  const status = (params.get('status') ?? '') as TaskStatus | ''
  const review = (params.get('review') ?? '') as ReviewStatus | ''
  const q = params.get('q') ?? ''
  const sort = (params.get('sort') ?? 'created_at') as 'created_at' | 'updated_at' | 'title'
  const order = (params.get('order') ?? 'desc') as 'asc' | 'desc'

  const [items, setItems] = useState<KnowledgeItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<KnowledgeItem | null>(null)
  const [qInput, setQInput] = useState(q)

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const load = useCallback(() => {
    setError(null)
    api
      .listKnowledge(pid, {
        type: type === 'all' ? undefined : type,
        status: status || undefined,
        review_status: review || undefined,
        q: q || undefined,
        sort,
        order,
      })
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load knowledge'))
  }, [pid, type, status, review, q, sort, order])

  useEffect(load, [load])

  useEffect(() => {
    setQInput(q)
  }, [q])

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items?.length ?? 0 }
    for (const i of items ?? []) c[i.type] = (c[i.type] ?? 0) + 1
    return c
  }, [items])

  return (
    <div>
      <PageHeader
        title="Knowledge base"
        subtitle="Decisions, tasks, events, risks, questions and entities extracted from your documents — each with linked source evidence."
      />

      {error && <div className="mb-4"><ErrorNote message={error} /></div>}

      {/* type tabs */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {TYPES.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setParam('type', t === 'all' ? '' : t)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium capitalize transition ${
              type === t
                ? 'bg-brand-500 text-white'
                : 'bg-navy-800 text-ink-400 hover:bg-navy-700 hover:text-ink-100'
            }`}
          >
            {t}
            {counts[t] != null && (
              <span className={`ml-1.5 ${type === t ? 'text-white/70' : 'text-ink-500'}`}>
                {counts[t]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* filters */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search size={14} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-500" />
          <input
            className={`${inputCls} w-56 pl-9`}
            placeholder="Search title, summary, details…"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') setParam('q', qInput.trim())
            }}
          />
        </div>
        {type === 'task' && (
          <select
            className={`${inputCls} w-auto`}
            value={status}
            onChange={(e) => setParam('status', e.target.value)}
          >
            <option value="">All task statuses</option>
            <option value="pending">pending</option>
            <option value="in_progress">in progress</option>
            <option value="completed">completed</option>
            <option value="blocked">blocked</option>
          </select>
        )}
        <select
          className={`${inputCls} w-auto`}
          value={review}
          onChange={(e) => setParam('review', e.target.value)}
        >
          <option value="">All review states</option>
          <option value="pending">pending</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
          <option value="flagged">flagged</option>
        </select>
        <div className="ml-auto flex items-center gap-2">
          <select
            className={`${inputCls} w-auto`}
            value={sort}
            onChange={(e) => setParam('sort', e.target.value)}
          >
            <option value="created_at">Newest first</option>
            <option value="updated_at">Recently updated</option>
            <option value="title">Title A–Z</option>
          </select>
          <button
            type="button"
            onClick={() => setParam('order', order === 'desc' ? 'asc' : 'desc')}
            className="rounded-lg border border-navy-600 bg-navy-800 px-3 py-2 text-xs text-ink-300 hover:bg-navy-700"
            title="Toggle sort order"
          >
            {order === 'desc' ? '↓ desc' : '↑ asc'}
          </button>
        </div>
      </div>

      {!items ? (
        <Spinner label="Loading knowledge…" />
      ) : items.length === 0 ? (
        <EmptyState
          title="No records match these filters"
          hint="Try clearing the search or choosing a different type."
        />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <KnowledgeItemCard key={item.id} item={item} onOpen={setSelected} />
          ))}
        </div>
      )}

      {selected && (
        <KnowledgeDetailModal
          item={selected}
          onClose={() => setSelected(null)}
          onChanged={(fresh) => {
            setSelected(fresh)
            load()
          }}
        />
      )}
    </div>
  )
}

