// Types mirroring the backend API contract (docs/API_CONTRACT.md).

export type KnowledgeType =
  | 'decision'
  | 'task'
  | 'event'
  | 'risk'
  | 'question'
  | 'entity'

export type TaskStatus = 'completed' | 'in_progress' | 'pending' | 'blocked'
export type EvidenceStatus = 'supported' | 'inferred' | 'conflicting' | 'unverified'
export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'flagged'
export type Severity = 'low' | 'medium' | 'high' | 'critical'
export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'processed'
  | 'failed'
  | 'needs_attention'

export interface ContinuityStats {
  completed: number
  in_progress: number
  pending: number
  blocked: number
  total: number
  percent: number | null
  available: boolean
}

export interface ProjectStats {
  documents: number
  decisions: number
  tasks: number
  open_tasks: number
  risks: number
  unresolved: number
  pending_reviews: number
  events: number
  entities: number
  conflicts: number
  continuity: ContinuityStats
}

export interface Project {
  id: number
  name: string
  description: string | null
  category: string | null
  objectives: string[]
  status: string
  created_at: string
  updated_at: string
  stats: ProjectStats | null
}

export interface Document {
  id: number
  project_id: number
  file_name: string
  file_type: string
  size_bytes: number
  status: DocumentStatus
  error: string | null
  page_count: number | null
  chunk_count: number
  uploaded_at: string
  processed_at: string | null
}

export interface DocumentPreview {
  document: Document
  text: string
  chunks: { id: number; page: number | null; text: string }[]
}

export interface Evidence {
  document_id: number
  document_name: string
  chunk_id: number | null
  page: number | null
  excerpt: string
}

export interface Relationship {
  type: string
  target_type: string | null
  target_id: number | null
  target_title: string | null
}

export interface KnowledgeItem {
  id: number
  project_id: number
  type: KnowledgeType
  title: string
  summary: string | null
  details: Record<string, unknown>
  status: string | null
  task_status: TaskStatus | null
  severity: Severity | null
  assignee: string | null
  due_date: string | null
  dependencies: string[]
  evidence_status: EvidenceStatus
  review_status: ReviewStatus
  evidence: Evidence[]
  relationships: Relationship[]
  created_at: string
  updated_at: string
  reviewed_by: string | null
  reviewed_at: string | null
}

export interface TimelineEntry {
  id: number
  date: string | null
  title: string
  type: 'event' | 'decision'
  description: string | null
  evidence: Evidence[]
}

export interface ConflictItemRef {
  id: number
  title: string
  type: string | null
  evidence: Evidence[]
}

export interface Conflict {
  id: number
  project_id: number
  topic: string
  items: ConflictItemRef[]
}

export interface Citation {
  document_id: number
  document_name: string
  page: number | null
  excerpt: string
}

export interface RelatedItem {
  id: number
  type: KnowledgeType
  title: string
}

export interface AskResponse {
  question: string
  answer: string
  evidence_status: 'supported' | 'insufficient'
  confidence: number
  citations: Citation[]
  related: RelatedItem[]
  warnings: string[]
}

export interface HandoverSection {
  key: string
  title: string
  content: string
}

export interface HandoverSummary {
  decisions: number
  tasks: number
  risks: number
  unresolved: number
  approved: number
  pending: number
}

export interface Handover {
  id: number
  project_id: number
  project_name: string
  audience: 'general' | 'engineer'
  version: number
  status: string
  generated_at: string
  sections: HandoverSection[]
  summary: HandoverSummary
}

export interface HandoverMeta {
  id: number
  project_id: number
  project_name: string
  audience: 'general' | 'engineer'
  version: number
  status: string
  generated_at: string
  summary: HandoverSummary
}

export interface AuditEntry {
  id: number
  project_id: number
  action: string
  entity_type: string | null
  entity_id: number | null
  entity_title: string | null
  reviewer: string | null
  detail: string | null
  created_at: string
}

export interface Settings {
  ai_configured: boolean
  ai_provider: string
  ai_model: string
  allowed_extensions: string[]
  max_file_mb: number
  max_files_per_upload: number
  data_disclosure: string
}

export interface Health {
  status: string
  version: string
  ai_configured: boolean
  ai_provider: string
}

export interface KnowledgeFilters {
  type?: KnowledgeType | 'all'
  status?: TaskStatus
  review_status?: ReviewStatus
  q?: string
  sort?: 'created_at' | 'updated_at' | 'title'
  order?: 'asc' | 'desc'
}