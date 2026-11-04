// Thin fetch-based API client. All paths go through the Vite proxy (/api, /health).
import type {
  AskResponse,
  AuditEntry,
  Conflict,
  Document,
  DocumentPreview,
  Handover,
  HandoverMeta,
  Health,
  KnowledgeFilters,
  KnowledgeItem,
  Project,
  Settings,
  TimelineEntry,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: init?.body && !(init.body instanceof FormData)
      ? { 'Content-Type': 'application/json' }
      : undefined,
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail) detail = JSON.stringify(body.detail)
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

function qs(params: Record<string, string | undefined>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v as string)}`)
  return parts.length ? `?${parts.join('&')}` : ''
}

export const api = {
  health: () => request<Health>('/health'),
  settings: () => request<Settings>('/api/settings'),

  // projects
  listProjects: () => request<Project[]>('/api/projects'),
  getProject: (id: number) => request<Project>(`/api/projects/${id}`),
  createProject: (body: {
    name: string
    description?: string
    category?: string
    objectives?: string[]
    status?: string
  }) => request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(body) }),
  patchProject: (id: number, body: Partial<{
    name: string
    description: string
    category: string
    objectives: string[]
    status: string
  }>) => request<Project>(`/api/projects/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteProject: (id: number) => request<{ deleted: boolean }>(`/api/projects/${id}`, { method: 'DELETE' }),

  // documents
  listDocuments: (projectId: number) =>
    request<Document[]>(`/api/projects/${projectId}/documents`),
  uploadDocuments: (projectId: number, files: File[]) => {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    return request<Document[]>(`/api/projects/${projectId}/documents`, {
      method: 'POST',
      body: fd,
    })
  },
  documentPreview: (docId: number) =>
    request<DocumentPreview>(`/api/documents/${docId}/preview`),
  processDocument: (docId: number) =>
    request<Document>(`/api/documents/${docId}/process`, { method: 'POST' }),
  deleteDocument: (docId: number) =>
    request<{ deleted: boolean }>(`/api/documents/${docId}`, { method: 'DELETE' }),

  // knowledge
  listKnowledge: (projectId: number, filters: KnowledgeFilters = {}) =>
    request<KnowledgeItem[]>(
      `/api/projects/${projectId}/knowledge${qs({
        type: filters.type,
        status: filters.status,
        review_status: filters.review_status,
        q: filters.q,
        sort: filters.sort,
        order: filters.order,
      })}`,
    ),
  getKnowledge: (id: number) => request<KnowledgeItem>(`/api/knowledge/${id}`),
  patchKnowledge: (id: number, body: Partial<{
    title: string
    summary: string
    details: Record<string, unknown>
    status: string
    task_status: string
    severity: string
    assignee: string
    due_date: string
    dependencies: string[]
  }>) => request<KnowledgeItem>(`/api/knowledge/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  reviewKnowledge: (id: number, body: {
    action: 'approve' | 'reject' | 'flag' | 'resolve_conflict'
    reviewer?: string
    note?: string
  }) => request<KnowledgeItem>(`/api/knowledge/${id}/review`, {
    method: 'POST',
    body: JSON.stringify(body),
  }),

  // timeline + conflicts
  timeline: (projectId: number) =>
    request<TimelineEntry[]>(`/api/projects/${projectId}/timeline`),
  conflicts: (projectId: number) =>
    request<Conflict[]>(`/api/projects/${projectId}/conflicts`),

  // assistant
  ask: (projectId: number, question: string) =>
    request<AskResponse>(`/api/projects/${projectId}/ask`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),

  // handover
  listHandovers: (projectId: number) =>
    request<HandoverMeta[]>(`/api/projects/${projectId}/handovers`),
  createHandover: (projectId: number, audience: 'general' | 'engineer') =>
    request<Handover>(`/api/projects/${projectId}/handovers`, {
      method: 'POST',
      body: JSON.stringify({ audience }),
    }),
  getHandover: (id: number) => request<Handover>(`/api/handovers/${id}`),
  handoverDownloadUrl: (id: number) => `/api/handovers/${id}/download`,

  // audit
  audit: (projectId: number, limit = 100) =>
    request<AuditEntry[]>(`/api/projects/${projectId}/audit${qs({ limit: String(limit) })}`),
}

// Poll a project's documents until none are processing/uploaded.
export async function pollDocuments(
  projectId: number,
  onTick?: (docs: Document[]) => void,
  intervalMs = 2500,
  timeoutMs = 120000,
): Promise<Document[]> {
  const start = Date.now()
  for (;;) {
    const docs = await api.listDocuments(projectId)
    onTick?.(docs)
    const pending = docs.some((d) => d.status === 'processing' || d.status === 'uploaded')
    if (!pending) return docs
    if (Date.now() - start > timeoutMs) return docs
    await new Promise((r) => setTimeout(r, intervalMs))
  }
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return 'Not specified'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDate(iso: string | null): string {
  if (!iso) return 'Not specified'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}