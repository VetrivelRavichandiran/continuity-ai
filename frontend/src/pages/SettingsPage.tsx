import { useEffect, useState } from 'react'
import { Cpu, FileText, Info, ShieldCheck } from 'lucide-react'
import { api } from '../lib/api'
import type { Health, Settings } from '../lib/types'
import { Badge, Card, ErrorNote, PageHeader, Spinner } from '../components/ui'

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.settings().then(setSettings).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load settings'))
    api.health().then(setHealth).catch(() => {})
  }, [])

  if (error) return <ErrorNote message={error} />
  if (!settings) return <Spinner label="Loading settings…" />

  return (
    <div>
      <PageHeader title="Settings" subtitle="Runtime information about this CONTINUITY AI instance." />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card className="p-5">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold tracking-wide text-ink-400 uppercase">
            <Cpu size={14} /> AI provider
          </div>
          <div className="space-y-2 text-sm">
            <Row label="Status">
              <Badge
                tone={
                  settings.ai_configured
                    ? 'bg-teal-500/15 text-teal-300 border-teal-500/30'
                    : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                }
              >
                {settings.ai_configured ? 'configured' : 'not configured'}
              </Badge>
            </Row>
            <Row label="Provider">{settings.ai_provider}</Row>
            <Row label="Model">{settings.ai_model}</Row>
            <Row label="Version">{health?.version ?? '—'}</Row>
          </div>
          {!settings.ai_configured && (
            <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
              No LLM key is set. A deterministic local extractor is used and no
              document text leaves this machine.
            </div>
          )}
        </Card>

        <Card className="p-5">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold tracking-wide text-ink-400 uppercase">
            <FileText size={14} /> Upload limits
          </div>
          <div className="space-y-2 text-sm">
            <Row label="Allowed types">{settings.allowed_extensions.join(', ')}</Row>
            <Row label="Max file size">{settings.max_file_mb} MB</Row>
            <Row label="Max files per upload">{settings.max_files_per_upload}</Row>
          </div>
        </Card>

        <Card className="p-5 md:col-span-2">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold tracking-wide text-ink-400 uppercase">
            <ShieldCheck size={14} /> Data disclosure
          </div>
          <p className="text-sm leading-relaxed text-ink-300">{settings.data_disclosure}</p>
        </Card>

        <Card className="p-5 md:col-span-2">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold tracking-wide text-ink-400 uppercase">
            <Info size={14} /> About
          </div>
          <p className="text-sm leading-relaxed text-ink-300">
            CONTINUITY AI extracts decisions, tasks, events, risks, questions and
            entities from project documents, links every record to source evidence,
            detects conflicts between sources, answers questions grounded in the
            records, and generates structured handover documents with PDF export.
          </p>
        </Card>
      </div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-ink-400">{label}</span>
      <span className="text-right font-medium text-ink-100">{children}</span>
    </div>
  )
}