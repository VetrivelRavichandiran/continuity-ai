import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  FileText,
  FolderPlus,
  Network,
  Pencil,
  Plus,
  Trash2,
} from 'lucide-react'
import { api, formatDateTime } from '../lib/api'
import type { Project } from '../lib/types'
import {
  Button,
  Card,
  EmptyState,
  ErrorNote,
  Field,
  inputCls,
  Modal,
  PageHeader,
  ProgressBar,
  Spinner,
} from '../components/ui'

export default function Dashboard() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Project | null>(null)

  const load = () => {
    setError(null)
    api
      .listProjects()
      .then(setProjects)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load projects'))
  }
  useEffect(load, [])

  const remove = async (p: Project) => {
    if (!window.confirm(`Delete project "${p.name}" and ALL of its documents, knowledge and handovers?`)) return
    try {
      await api.deleteProject(p.id)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  return (
    <div>
      <PageHeader
        title="Projects"
        subtitle="Each project is an isolated knowledge base built from its uploaded documents."
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus size={15} /> New project
          </Button>
        }
      />

      {error && <div className="mb-4"><ErrorNote message={error} /></div>}

      {!projects ? (
        <Spinner label="Loading projects…" />
      ) : projects.length === 0 ? (
        <EmptyState
          title="No projects yet"
          hint="Create a project, upload its documents (PDF, DOCX, TXT, MD), and CONTINUITY AI will extract decisions, tasks, risks, events and entities with linked source evidence."
          action={
            <Button onClick={() => setCreating(true)}>
              <FolderPlus size={15} /> Create your first project
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {projects.map((p) => (
            <Card key={p.id} className="p-5" onClick={() => navigate(`/${p.id}`)}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-base font-semibold text-ink-50">{p.name}</div>
                  {p.category && (
                    <span className="mt-1 inline-block rounded-md bg-navy-800 px-2 py-0.5 text-[11px] text-ink-400">
                      {p.category}
                    </span>
                  )}
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    title="Edit"
                    onClick={(e) => {
                      e.stopPropagation()
                      setEditing(p)
                    }}
                    className="rounded-lg p-1.5 text-ink-500 hover:bg-navy-800 hover:text-ink-200"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    title="Delete"
                    onClick={(e) => {
                      e.stopPropagation()
                      remove(p)
                    }}
                    className="rounded-lg p-1.5 text-ink-500 hover:bg-red-500/15 hover:text-red-300"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {p.description && (
                <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-ink-400">{p.description}</p>
              )}

              {p.stats && (
                <div className="mt-4">
                  <div className="mb-1.5 flex items-center justify-between text-[11px] text-ink-500">
                    <span>
                      {p.stats.documents} docs · {p.stats.tasks} tasks · {p.stats.decisions} decisions
                    </span>
                    {p.stats.conflicts > 0 && (
                      <span className="inline-flex items-center gap-1 text-red-300">
                        <AlertTriangle size={11} /> {p.stats.conflicts} conflict
                        {p.stats.conflicts > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  {p.stats.continuity.available ? (
                    <div>
                      <ProgressBar
                        segments={[
                          { value: p.stats.continuity.completed, color: 'var(--color-teal-500)' },
                          { value: p.stats.continuity.in_progress, color: 'var(--color-brand-400)' },
                          { value: p.stats.continuity.pending, color: '#d97706' },
                          { value: p.stats.continuity.blocked, color: '#dc2626' },
                        ]}
                      />
                      <div className="mt-1 text-right text-[11px] text-ink-500">
                        {p.stats.continuity.percent}% complete
                      </div>
                    </div>
                  ) : (
                    <div className="text-[11px] text-ink-500 italic">No tasks recorded yet</div>
                  )}
                </div>
              )}

              <div className="mt-4 flex items-center justify-between border-t border-navy-800 pt-3">
                <span className="text-[11px] text-ink-500">Updated {formatDateTime(p.updated_at)}</span>
                <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-300">
                  Open <ArrowRight size={13} />
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}

      <ProjectFormModal
        open={creating || editing !== null}
        project={editing}
        onClose={() => {
          setCreating(false)
          setEditing(null)
        }}
        onSaved={() => {
          setCreating(false)
          setEditing(null)
          load()
        }}
      />
    </div>
  )
}

export function ProjectFormModal({
  open,
  project,
  onClose,
  onSaved,
}: {
  open: boolean
  project: Project | null
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [objectives, setObjectives] = useState('')
  const [status, setStatus] = useState('active')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setName(project?.name ?? '')
      setDescription(project?.description ?? '')
      setCategory(project?.category ?? '')
      setObjectives((project?.objectives ?? []).join('\n'))
      setStatus(project?.status ?? 'active')
      setError(null)
    }
  }, [open, project])

  const submit = async () => {
    if (!name.trim()) {
      setError('Project name is required')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const body = {
        name: name.trim(),
        description: description.trim() || undefined,
        category: category.trim() || undefined,
        objectives: objectives
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        status,
      }
      if (project) {
        await api.patchProject(project.id, body)
      } else {
        await api.createProject(body)
      }
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save project')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={project ? 'Edit project' : 'New project'}>
      <div className="space-y-4">
        {error && <ErrorNote message={error} />}
        <Field label="Name *">
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Autonomous Delivery Robot Development" />
        </Field>
        <Field label="Description">
          <textarea
            className={`${inputCls} min-h-20 resize-y`}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What is this project about?"
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Category">
            <input className={inputCls} value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. R&D" />
          </Field>
          <Field label="Status">
            <select className={inputCls} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="active">active</option>
              <option value="on_hold">on_hold</option>
              <option value="completed">completed</option>
              <option value="archived">archived</option>
            </select>
          </Field>
        </div>
        <Field label="Objectives" hint="One per line.">
          <textarea
            className={`${inputCls} min-h-24 resize-y`}
            value={objectives}
            onChange={(e) => setObjectives(e.target.value)}
            placeholder={'Ship a working prototype\nPass thermal validation'}
          />
        </Field>
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={busy}>
            {project ? 'Save changes' : <><Plus size={15} /> Create project</>}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export function ProjectHeader({
  project,
  onEdit,
}: {
  project: Project
  onEdit: () => void
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-2xl font-semibold tracking-tight text-ink-50">{project.name}</h1>
          <button
            type="button"
            onClick={onEdit}
            title="Edit project"
            className="rounded-lg p-1.5 text-ink-500 hover:bg-navy-800 hover:text-ink-200"
          >
            <Pencil size={14} />
          </button>
        </div>
        {project.description && (
          <p className="mt-1 max-w-2xl text-sm text-ink-400">{project.description}</p>
        )}
      </div>
      {project.stats && (
        <div className="flex items-center gap-4 text-xs text-ink-400">
          <span className="inline-flex items-center gap-1.5">
            <FileText size={13} className="text-brand-300" /> {project.stats.documents} documents
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Network size={13} className="text-brand-300" /> {project.stats.decisions + project.stats.tasks + project.stats.risks + project.stats.unresolved + project.stats.events + project.stats.entities} records
          </span>
        </div>
      )}
    </div>
  )
}