import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Eye,
  FileText,
  Loader2,
  RefreshCw,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import { api, formatBytes, formatDateTime, pollDocuments } from '../lib/api'
import type { Document, DocumentPreview } from '../lib/types'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorNote,
  IconButton,
  Modal,
  PageHeader,
  Spinner,
} from '../components/ui'

const STATUS_TONE: Record<string, string> = {
  uploaded: 'bg-ink-500/15 text-ink-300 border-ink-500/30',
  processing: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
  processed: 'bg-teal-500/15 text-teal-300 border-teal-500/30',
  failed: 'bg-red-500/15 text-red-300 border-red-500/30',
  needs_attention: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
}

export default function DocumentsPage() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const [docs, setDocs] = useState<Document[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState<DocumentPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const load = useCallback(() => {
    api
      .listDocuments(pid)
      .then(setDocs)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load documents'))
  }, [pid])

  useEffect(load, [load])

  // poll while anything is processing
  const anyProcessing = (docs ?? []).some(
    (d) => d.status === 'processing' || d.status === 'uploaded',
  )
  useEffect(() => {
    if (!anyProcessing) return
    const t = setInterval(load, 2500)
    return () => clearInterval(t)
  }, [anyProcessing, load])

  const upload = async (files: File[]) => {
    if (!files.length) return
    setUploading(true)
    setError(null)
    try {
      await api.uploadDocuments(pid, files)
      await pollDocuments(pid, setDocs)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
      load()
    } finally {
      setUploading(false)
    }
  }

  const reprocess = async (doc: Document) => {
    setError(null)
    try {
      setDocs((prev) =>
        prev?.map((d) => (d.id === doc.id ? { ...d, status: 'processing', error: null } : d)) ?? null,
      )
      await api.processDocument(doc.id)
      await pollDocuments(pid, setDocs)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Processing failed')
      load()
    }
  }

  const remove = async (doc: Document) => {
    if (!window.confirm(`Delete "${doc.file_name}"? Knowledge items that cite only this document will be removed.`)) return
    try {
      await api.deleteDocument(doc.id)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  const openPreview = async (doc: Document) => {
    setPreviewLoading(true)
    setPreview(null)
    try {
      setPreview(await api.documentPreview(doc.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load preview')
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Documents"
        subtitle="Upload project documents. Text is extracted, chunked, and knowledge is extracted with linked source evidence."
      />

      {error && <div className="mb-4"><ErrorNote message={error} /></div>}

      {/* dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          upload(Array.from(e.dataTransfer.files))
        }}
        onClick={() => fileInput.current?.click()}
        className={`mb-6 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
          dragOver
            ? 'border-brand-400 bg-brand-500/10'
            : 'border-navy-600 bg-navy-900 hover:border-brand-500/50'
        }`}
      >
        <input
          ref={fileInput}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={(e) => {
            upload(Array.from(e.target.files ?? []))
            e.target.value = ''
          }}
        />
        {uploading ? (
          <>
            <Loader2 size={28} className="animate-spin text-brand-300" />
            <div className="text-sm font-medium text-ink-200">Uploading & processing…</div>
          </>
        ) : (
          <>
            <Upload size={28} className="text-brand-300" />
            <div className="text-sm font-medium text-ink-200">
              Drop files here or click to browse
            </div>
            <div className="text-xs text-ink-500">
              PDF, DOCX, TXT, MD · max 15 MB each · max 20 files per upload
            </div>
          </>
        )}
      </div>

      {!docs ? (
        <Spinner label="Loading documents…" />
      ) : docs.length === 0 ? (
        <EmptyState
          title="No documents yet"
          hint="Upload project documents to start building the knowledge base. The sample data folder in the project root has four files that work well."
        />
      ) : (
        <div className="space-y-3">
          {docs.map((doc) => (
            <Card key={doc.id} className="flex flex-wrap items-center gap-4 p-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy-800 text-brand-300">
                <FileText size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium text-ink-50">{doc.file_name}</span>
                  <Badge tone={STATUS_TONE[doc.status] ?? STATUS_TONE.uploaded}>
                    {doc.status === 'processing' && <Loader2 size={11} className="animate-spin" />}
                    {doc.status}
                  </Badge>
                </div>
                <div className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-ink-500">
                  <span>{doc.file_type}</span>
                  <span>{formatBytes(doc.size_bytes)}</span>
                  {doc.page_count != null && <span>{doc.page_count} pages</span>}
                  <span>{doc.chunk_count} chunks</span>
                  <span>uploaded {formatDateTime(doc.uploaded_at)}</span>
                </div>
                {doc.error && (
                  <div className="mt-1.5 rounded-md border border-red-500/30 bg-red-500/10 px-2 py-1 text-[11px] text-red-300">
                    {doc.error}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <IconButton title="Preview" onClick={() => openPreview(doc)} disabled={doc.status !== 'processed'}>
                  <Eye size={15} />
                </IconButton>
                <IconButton title="Re-process" onClick={() => reprocess(doc)} disabled={doc.status === 'processing'}>
                  <RefreshCw size={15} className={doc.status === 'processing' ? 'animate-spin' : ''} />
                </IconButton>
                <IconButton title="Delete" danger onClick={() => remove(doc)}>
                  <Trash2 size={15} />
                </IconButton>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* preview modal */}
      <Modal
        open={preview !== null || previewLoading}
        onClose={() => setPreview(null)}
        title={preview?.document.file_name ?? 'Document preview'}
        wide
      >
        {previewLoading ? (
          <Spinner label="Loading preview…" />
        ) : preview && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2 text-xs text-ink-400">
              <Badge tone={STATUS_TONE[preview.document.status]}>
                {preview.document.status}
              </Badge>
              <span>{preview.document.chunk_count} chunks</span>
              {preview.document.page_count != null && <span>{preview.document.page_count} pages</span>}
              <span>{formatBytes(preview.document.size_bytes)}</span>
            </div>
            <div>
              <div className="mb-2 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                Extracted text
              </div>
              <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-lg border border-navy-700 bg-navy-850 p-4 font-mono text-xs leading-relaxed text-ink-300">
                {preview.text || '(no extractable text)'}
              </pre>
            </div>
            <div>
              <div className="mb-2 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                Chunks ({preview.chunks.length})
              </div>
              <div className="space-y-2">
                {preview.chunks.map((c) => (
                  <div key={c.id} className="rounded-lg border border-navy-700 bg-navy-850 p-3">
                    <div className="mb-1 text-[11px] text-ink-500">
                      chunk #{c.id}
                      {c.page != null && ` · page ${c.page}`}
                    </div>
                    <div className="line-clamp-3 text-xs leading-relaxed text-ink-300">{c.text}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-end">
              <Button variant="ghost" onClick={() => setPreview(null)}>
                <X size={14} /> Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}