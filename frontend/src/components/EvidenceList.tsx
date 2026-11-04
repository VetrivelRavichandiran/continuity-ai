import { useState } from 'react'
import { ChevronDown, ChevronRight, FileText } from 'lucide-react'
import type { Evidence } from '../lib/types'

export function EvidenceList({ evidence, max = 3 }: { evidence: Evidence[]; max?: number }) {
  const [open, setOpen] = useState(false)
  if (!evidence.length) {
    return <span className="text-xs text-ink-500 italic">No source evidence linked</span>
  }
  const shown = open ? evidence : evidence.slice(0, max)
  return (
    <div className="space-y-2">
      {shown.map((ev, i) => (
        <div
          key={`${ev.document_id}-${ev.chunk_id}-${i}`}
          className="rounded-lg border border-navy-700 bg-navy-850 p-3"
        >
          <div className="mb-1 flex items-center gap-2 text-xs text-ink-400">
            <FileText size={13} className="shrink-0 text-brand-300" />
            <span className="font-medium text-ink-300">{ev.document_name}</span>
            {ev.page != null && <span className="ml-auto shrink-0">page {ev.page}</span>}
          </div>
          <blockquote className="border-l-2 border-brand-500/40 pl-3 text-xs leading-relaxed text-ink-300 italic">
            “{ev.excerpt}”
          </blockquote>
        </div>
      ))}
      {evidence.length > max && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-1 text-xs font-medium text-brand-300 hover:text-brand-400"
        >
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          {open ? 'Show less' : `Show ${evidence.length - max} more`}
        </button>
      )}
    </div>
  )
}