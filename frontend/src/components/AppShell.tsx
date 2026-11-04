import { useEffect, useState } from 'react'
import { NavLink, Outlet, useParams, useOutletContext } from 'react-router-dom'
import {
  AlertTriangle,
  FileText,
  FolderOpen,
  History,
  LayoutDashboard,
  MessageSquareText,
  Moon,
  Network,
  ScrollText,
  Settings as SettingsIcon,
  ShieldCheck,
  Sun,
} from 'lucide-react'
import { api } from '../lib/api'
import type { Project, Settings } from '../lib/types'
import { Badge } from './ui'

const NAV = [
  { to: '', end: true, label: 'Overview', icon: LayoutDashboard },
  { to: 'documents', label: 'Documents', icon: FileText },
  { to: 'knowledge', label: 'Knowledge', icon: Network },
  { to: 'timeline', label: 'Timeline', icon: History },
  { to: 'conflicts', label: 'Conflicts', icon: AlertTriangle },
  { to: 'assistant', label: 'Assistant', icon: MessageSquareText },
  { to: 'handover', label: 'Handover', icon: ScrollText },
  { to: 'audit', label: 'Audit Log', icon: ShieldCheck },
]

export function ThemeToggle() {
  const [theme, setTheme] = useState<string>(
    () => localStorage.getItem('continuity-theme') ?? 'dark',
  )
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    localStorage.setItem('continuity-theme', next)
    document.documentElement.setAttribute('data-theme', next)
  }
  return (
    <button
      type="button"
      onClick={toggle}
      title="Toggle theme"
      className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-ink-400 transition hover:bg-navy-800 hover:text-ink-100"
    >
      {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}

export interface ShellContext {
  project: Project | null
  refreshProject: () => void
  settings: Settings | null
}

export function useShell() {
  return useOutletContext<ShellContext>()
}

export function AppShell() {
  const { projectId } = useParams()
  const [project, setProject] = useState<Project | null>(null)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const pid = projectId ? Number(projectId) : null

  useEffect(() => {
    let live = true
    api
      .settings()
      .then((s) => live && setSettings(s))
      .catch(() => {})
    if (pid) {
      api
        .getProject(pid)
        .then((p) => live && setProject(p))
        .catch(() => live && setProject(null))
    } else {
      setProject(null)
    }
    return () => {
      live = false
    }
  }, [pid, reloadKey])

  const refreshProject = () => setReloadKey((k) => k + 1)

  return (
    <div className="flex h-full">
      {/* sidebar */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-navy-800 bg-navy-900">
        <div className="flex items-center gap-2.5 px-5 pt-5 pb-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500/20 text-brand-300">
            <Network size={18} />
          </div>
          <div>
            <div className="text-sm font-bold tracking-wide text-ink-50">CONTINUITY AI</div>
            <div className="text-[10px] tracking-wider text-ink-500 uppercase">
              project knowledge
            </div>
          </div>
        </div>

        {project ? (
          <div className="mx-3 mb-3 rounded-lg border border-navy-700 bg-navy-850 px-3 py-2.5">
            <div className="flex items-center gap-2 text-[11px] text-ink-500">
              <FolderOpen size={12} /> Active project
            </div>
            <div className="mt-0.5 truncate text-sm font-medium text-ink-100" title={project.name}>
              {project.name}
            </div>
          </div>
        ) : (
          <div className="mx-3 mb-3 rounded-lg border border-dashed border-navy-700 px-3 py-2.5 text-[11px] text-ink-500">
            Select a project to begin
          </div>
        )}

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? 'bg-brand-500/15 text-brand-300'
                  : 'text-ink-400 hover:bg-navy-800 hover:text-ink-100'
              }`
            }
          >
            <LayoutDashboard size={16} />
            Projects
          </NavLink>

          {pid &&
            NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={`/${pid}/${to}`}
                end={end}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive
                      ? 'bg-brand-500/15 text-brand-300'
                      : 'text-ink-400 hover:bg-navy-800 hover:text-ink-100'
                  }`
                }
              >
                <Icon size={16} />
                {label}
                {to === 'conflicts' && (project?.stats?.conflicts ?? 0) > 0 && (
                  <span className="ml-auto rounded-full bg-red-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-red-300">
                    {project?.stats?.conflicts}
                  </span>
                )}
              </NavLink>
            ))}
        </nav>

        <div className="border-t border-navy-800 p-3">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? 'bg-brand-500/15 text-brand-300'
                  : 'text-ink-400 hover:bg-navy-800 hover:text-ink-100'
              }`
            }
          >
            <SettingsIcon size={16} />
            Settings
          </NavLink>
          <div className="mt-2 flex items-center justify-between px-3">
            <Badge
              tone={
                settings?.ai_configured
                  ? 'bg-teal-500/15 text-teal-300 border-teal-500/30'
                  : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
              }
            >
              {settings?.ai_configured
                ? `AI: ${settings.ai_provider}`
                : 'Deterministic mode'}
            </Badge>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* main */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 py-6">
          {!settings?.ai_configured && pid && (
            <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-300">
              AI key not configured — using deterministic extraction. Answers are
              grounded in retrieved passages only.
            </div>
          )}
          <Outlet context={{ project, refreshProject, settings } satisfies ShellContext} />
        </div>
      </main>
    </div>
  )
}