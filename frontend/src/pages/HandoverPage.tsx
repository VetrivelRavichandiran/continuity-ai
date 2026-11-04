import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { Download, FileOutput, Loader2, ScrollText } from 'lucide-react'
import { api, formatDateTime } from '../lib/api'
import type { Handover, HandoverMeta } from '../lib/types'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorNote,
  PageHeader,
  Spinner,
} from '../components/ui'

// minimal markdown-lite renderer: "## " headings, "- " bullets, **bold**
function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**') && p.length > 4) {
      return (
        <strong key={`${keyPrefix}-${i}`} className="font-semibold text-ink-50">
          {p.slice(2, -2)}
        </strong>
      )
    }
    return <Fragment key={`${keyPrefix}-${i}`}>{p}</Fragment>
  })
}

function MarkdownLite({ content }: { content: string }) {
  const lines = (content || '').split('\n')
  const out: ReactNode[] = []
  let bulletBuf: string[] = []
  const flushBullets = (key: string) => {
    if (bulletBuf.length) {
      out.push(
        <ul key={key} className="my-1.5 space-y-1 pl-1">
          {bulletBuf.map((b, i) => (
            <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-200">
              <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
              <span>{renderInline(b, `${key}-${i}`)}</span>
            </li>
          ))}
        </ul>,
      )
      bulletBuf = []
    }
  }
  lines.forEach((raw, i) => {
    const line = raw.trimEnd()
    if (line.startsWith('## ')) {
      flushBullets(`u${i}`)
      out.push(
        <h4 key={i} className="mt-3 mb-1 text-sm font-semibold text-brand-300">
          {renderInline(line.slice(3), `h${i}`)}
        </h4>,
      )
    } else if (line.startsWith('- ')) {
      bulletBuf.push(line.slice(2))
    } else if (line.trim() === '') {
      flushBullets(`u${i}`)
    } else {
      flushBullets(`u${i}`)
      out.push(
        <p key={i} className="my-1.5 text-sm leading-relaxed text-ink-200">
          {renderInline(line, `p${i}`)}
        </p>,
      )
    }
  })
  flushBullets('uend')
  return <div>{out}</div>
}

export default function HandoverPage() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const [list, setList] = useState<HandoverMeta[] | null>(null)
  const [selected, setSelected] = useState<Handover | null>(null)
  const [generating, setGenerating] = useState<'general' | 'engineer' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const load = () => {
    api
      .listHandovers(pid)
      .then(setList)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load handovers'))
  }
  useEffect(load, [pid])

  const generate = async (audience: 'general' | 'engineer') => {
    setGenerating(audience)
    setError(null)
    try {
      const h = await api.createHandover(pid, audience)
      setSelected(h)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Handover generation failed')
    } finally {
      setGenerating(null)
    }
  }

  const openMeta = async (meta: HandoverMeta) => {
    setLoadingDetail(true)
    setError(null)
    try {
      setSelected(await api.getHandover(meta.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load handover')
    } finally {
      setLoadingDetail(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Handover"
        subtitle="Generate a structured handover document from verified project knowledge — 15 sections, grounded in records only, downloadable as PDF."
        actions={
          <>
            <Button
              variant="secondary"
              onClick={() => generate('general')}
              disabled={generating !== null}
            >
              {generating === 'general' ? <Loader2 size={15} className="animate-spin" /> : <FileOutput size={15} />}
              General
            </Button>
            <Button onClick={() => generate('engineer')} disabled={generating !== null}>
              {generating === 'engineer' ? <Loader2 size={15} className="animate-spin" /> : <FileOutput size={15} />}
              Engineer
            </Button>
          </>
        }
      />

      {error && <div className="mb-4"><ErrorNote message={error} /></div>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* history */}
        <div className="lg:col-span-1">
          <div className="mb-2 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
            Generated handovers
          </div>
          {!list ? (
            <Spinner label="Loading…" />
          ) : list.length === 0 ? (
            <EmptyState
              title="No handovers yet"
              hint="Generate one to get a 15-section handover document with PDF download."
            />
          ) : (
            <div className="space-y-2">
              {list.map((h) => (
                <Card
                  key={h.id}
                  className={`p-3.5 ${selected?.id === h.id ? 'border-brand-400' : ''}`}
                  onClick={() => openMeta(h)}
                >
                  <div className="flex items-center gap-2">
                    <ScrollText size={15} className="text-brand-300" />
                    <span className="text-sm font-medium text-ink-100">
                      v{h.version} · {h.audience}
                    </span>
                    <span className="ml-auto text-[11px] text-ink-500">#{h.id}</span>
                  </div>
                  <div className="mt-1 text-[11px] text-ink-500">
                    {formatDateTime(h.generated_at)}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* detail */}
        <div className="lg:col-span-2">
          {loadingDetail ? (
            <Spinner label="Loading handover…" />
          ) : !selected ? (
            <EmptyState
              title="Select or generate a handover"
              hint="The handover assembles overview, status, completed / in-progress / pending work, decisions with reasoning, architecture changes, unresolved issues, risks, dependencies, milestones, next actions, evidence references and verification status."
            />
          ) : (
            <Card className="p-6">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-navy-700 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-ink-50">{selected.project_name}</h2>
                    <Badge tone="bg-brand-500/15 text-brand-300 border-brand-500/30">
                      v{selected.version}
                    </Badge>
                    <Badge>{selected.audience}</Badge>
                  </div>
                  <div className="mt-1 text-xs text-ink-500">
                    Generated {formatDateTime(selected.generated_at)} · {selected.status}
                  </div>
                </div>
                <a href={api.handoverDownloadUrl(selected.id)}>
                  <Button>
                    <Download size={15} /> Download PDF
                  </Button>
                </a>
              </div>

              {/* summary chips */}
              <div className="mt-4 flex flex-wrap gap-2">
                <Chip label="decisions" value={selected.summary.decisions} />
                <Chip label="tasks" value={selected.summary.tasks} />
                <Chip label="risks" value={selected.summary.risks} />
                <Chip label="unresolved" value={selected.summary.unresolved} />
                <Chip label="approved" value={selected.summary.approved} />
                <Chip label="pending review" value={selected.summary.pending} />
              </div>

              {/* sections */}
              <div className="mt-6 space-y-6">
                {selected.sections.map((s) => (
                  <section key={s.key}>
                    <h3 className="mb-2 border-b border-navy-700 pb-1.5 text-base font-semibold text-ink-50">
                      {s.title}
                    </h3>
                    <MarkdownLite content={s.content} />
                  </section>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

function Chip({ label, value }: { label: string; value: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-navy-700 bg-navy-850 px-2.5 py-1 text-xs text-ink-400">
      {label}
      <span className="font-semibold text-ink-100">{value}</span>
    </span>
  )
}