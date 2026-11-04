import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  Clock,
  FileText,
  GitBranch,
  HelpCircle,
  ListChecks,
  Network,
  ShieldCheck,
  Target,
  User,
} from 'lucide-react'
import { api } from '../lib/api'
import type { Project } from '../lib/types'
import {
  Card,
  ErrorNote,
  ProgressRing,
  Spinner,
  StatCard,
} from '../components/ui'
import { ProjectFormModal, ProjectHeader } from './Dashboard'

export default function ProjectOverview() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    api
      .getProject(pid)
      .then(setProject)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load project'))
  }, [pid])

  if (error) return <ErrorNote message={error} />
  if (!project) return <Spinner label="Loading project…" />

  const s = project.stats
  const c = s?.continuity

  return (
    <div>
      <ProjectHeader project={project} onEdit={() => setEditing(true)} />

      {s && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              label="Documents"
              value={s.documents}
              icon={<FileText size={18} />}
              hint={`${s.documents === 1 ? '1' : s.documents} uploaded`}
            />
            <StatCard
              label="Decisions"
              value={s.decisions}
              icon={<GitBranch size={18} />}
              tone="text-purple-300"
            />
            <StatCard
              label="Risks"
              value={s.risks}
              icon={<AlertTriangle size={18} />}
              tone="text-orange-300"
            />
            <StatCard
              label="Unresolved"
              value={s.unresolved}
              icon={<HelpCircle size={18} />}
              tone="text-amber-300"
            />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* continuity */}
            <Card className="flex flex-col items-center justify-center p-6">
              <div className="mb-3 self-start text-xs font-medium tracking-wide text-ink-400 uppercase">
                Project continuity
              </div>
              {c?.available ? (
                <>
                  <ProgressRing percent={c.percent ?? 0} sub={`${c.completed}/${c.total} tasks done`} />
                  <div className="mt-4 grid w-full grid-cols-2 gap-2 text-xs">
                    <Legend color="var(--color-teal-500)" label="Completed" value={c.completed} />
                    <Legend color="var(--color-brand-400)" label="In progress" value={c.in_progress} />
                    <Legend color="#d97706" label="Pending" value={c.pending} />
                    <Legend color="#dc2626" label="Blocked" value={c.blocked} />
                  </div>
                </>
              ) : (
                <div className="py-8 text-sm text-ink-500 italic">
                  Unavailable — no tasks recorded yet.
                </div>
              )}
            </Card>

            {/* review + conflicts */}
            <Card className="p-6">
              <div className="text-xs font-medium tracking-wide text-ink-400 uppercase">
                Verification
              </div>
              <div className="mt-4 space-y-3">
                <Row
                  icon={<ShieldCheck size={16} className="text-teal-300" />}
                  label="Pending reviews"
                  value={s.pending_reviews}
                  to={`/${pid}/knowledge?review=pending`}
                />
                <Row
                  icon={<AlertTriangle size={16} className="text-red-300" />}
                  label="Open conflicts"
                  value={s.conflicts}
                  to={`/${pid}/conflicts`}
                />
                <Row
                  icon={<ListChecks size={16} className="text-brand-300" />}
                  label="Open tasks"
                  value={s.open_tasks}
                  to={`/${pid}/knowledge?type=task`}
                />
                <Row
                  icon={<CircleHelp size={16} className="text-amber-300" />}
                  label="Open questions"
                  value={s.unresolved}
                  to={`/${pid}/knowledge?type=question`}
                />
              </div>
            </Card>

            {/* knowledge mix */}
            <Card className="p-6">
              <div className="text-xs font-medium tracking-wide text-ink-400 uppercase">
                Knowledge base
              </div>
              <div className="mt-4 space-y-3">
                <Row icon={<GitBranch size={16} className="text-purple-300" />} label="Decisions" value={s.decisions} to={`/${pid}/knowledge?type=decision`} />
                <Row icon={<ListChecks size={16} className="text-blue-300" />} label="Tasks" value={s.tasks} to={`/${pid}/knowledge?type=task`} />
                <Row icon={<Clock size={16} className="text-purple-300" />} label="Events" value={s.events} to={`/${pid}/timeline`} />
                <Row icon={<User size={16} className="text-teal-300" />} label="Entities" value={s.entities} to={`/${pid}/knowledge?type=entity`} />
              </div>
            </Card>
          </div>

          {/* objectives */}
          {project.objectives.length > 0 && (
            <Card className="mt-4 p-6">
              <div className="mb-3 flex items-center gap-2 text-xs font-medium tracking-wide text-ink-400 uppercase">
                <Target size={14} /> Project objectives
              </div>
              <ul className="space-y-2">
                {project.objectives.map((o, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-ink-200">
                    <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-teal-400" />
                    {o}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* quick actions */}
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to={`/${pid}/documents`}>
              <Card className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-ink-200 transition hover:border-brand-400">
                <FileText size={15} className="text-brand-300" /> Manage documents
              </Card>
            </Link>
            <Link to={`/${pid}/knowledge`}>
              <Card className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-ink-200 transition hover:border-brand-400">
                <Network size={15} className="text-brand-300" /> Browse knowledge
              </Card>
            </Link>
            <Link to={`/${pid}/assistant`}>
              <Card className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-ink-200 transition hover:border-brand-400">
                <CircleHelp size={15} className="text-brand-300" /> Ask the assistant
              </Card>
            </Link>
            <Link to={`/${pid}/handover`}>
              <Card className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-ink-200 transition hover:border-brand-400">
                <ShieldCheck size={15} className="text-brand-300" /> Generate handover
              </Card>
            </Link>
          </div>
        </>
      )}

      <ProjectFormModal
        open={editing}
        project={project}
        onClose={() => setEditing(false)}
        onSaved={() => {
          setEditing(false)
          api.getProject(pid).then(setProject).catch(() => {})
        }}
      />
    </div>
  )
}

function Legend({ color, label, value }: { color: string; label: string; value: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
      <span className="text-ink-400">{label}</span>
      <span className="ml-auto font-medium text-ink-100">{value}</span>
    </div>
  )
}

function Row({
  icon,
  label,
  value,
  to,
}: {
  icon: React.ReactNode
  label: string
  value: number
  to: string
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 rounded-lg border border-navy-700 bg-navy-850 px-3 py-2.5 transition hover:border-navy-600"
    >
      {icon}
      <span className="text-sm text-ink-300">{label}</span>
      <span className="ml-auto text-sm font-semibold text-ink-50">{value}</span>
    </Link>
  )
}