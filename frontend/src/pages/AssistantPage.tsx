import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle, FileText, Send, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import type { AskResponse } from '../lib/types'
import { Badge, Card, ErrorNote, PageHeader } from '../components/ui'

const SUGGESTIONS = [
  'Why was Controller A selected?',
  'What is the state of integration testing?',
  'What risks does the project face?',
  'Who owns the thermal validation work?',
]

interface Turn {
  question: string
  answer: AskResponse | null
  error?: string
}

export default function AssistantPage() {
  const { projectId } = useParams()
  const pid = Number(projectId)
  const [turns, setTurns] = useState<Turn[]>([])
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, busy])

  const ask = async (q: string) => {
    const text = q.trim()
    if (!text || busy) return
    setBusy(true)
    setQuestion('')
    setTurns((prev) => [...prev, { question: text, answer: null }])
    try {
      const res = await api.ask(pid, text)
      setTurns((prev) => {
        const next = [...prev]
        next[next.length - 1] = { question: text, answer: res }
        return next
      })
    } catch (e) {
      setTurns((prev) => {
        const next = [...prev]
        next[next.length - 1] = {
          question: text,
          answer: null,
          error: e instanceof Error ? e.message : 'Question failed',
        }
        return next
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Assistant"
        subtitle="Ask questions about the project. Answers are grounded in retrieved passages — the assistant never invents facts, and says so when evidence is insufficient."
      />

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {turns.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-500/15 text-brand-300">
              <Sparkles size={26} />
            </div>
            <div>
              <div className="text-sm font-medium text-ink-200">
                Ask anything about this project
              </div>
              <div className="mt-1 text-xs text-ink-500">
                Try one of these:
              </div>
            </div>
            <div className="flex max-w-lg flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => ask(s)}
                  className="rounded-full border border-navy-600 bg-navy-850 px-3 py-1.5 text-xs text-ink-300 transition hover:border-brand-400 hover:text-brand-300"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t, i) => (
          <div key={i} className="space-y-3">
            <div className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand-500/20 px-4 py-2.5 text-sm text-ink-100">
                {t.question}
              </div>
            </div>
            <div className="flex justify-start">
              <div className="max-w-[85%] space-y-3">
                {t.error && <ErrorNote message={t.error} />}
                {!t.answer && !t.error && (
                  <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-navy-700 bg-navy-900 px-4 py-3 text-sm text-ink-400">
                    <span className="h-2 w-2 animate-pulse-soft rounded-full bg-brand-400" />
                    Searching project records…
                  </div>
                )}
                {t.answer && (
                  <Card className="rounded-2xl rounded-bl-sm p-4">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <Badge
                        tone={
                          t.answer.evidence_status === 'supported'
                            ? 'bg-teal-500/15 text-teal-300 border-teal-500/30'
                            : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                        }
                      >
                        {t.answer.evidence_status === 'supported'
                          ? 'supported by sources'
                          : 'insufficient evidence'}
                      </Badge>
                      <span className="text-[11px] text-ink-500">
                        confidence {Math.round(t.answer.confidence * 100)}%
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap text-ink-100">
                      {t.answer.answer}
                    </p>

                    {t.answer.warnings.length > 0 && (
                      <div className="mt-3 space-y-1.5">
                        {t.answer.warnings.map((w, j) => (
                          <div
                            key={j}
                            className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300"
                          >
                            <AlertTriangle size={13} className="mt-0.5 shrink-0" />
                            {w}
                          </div>
                        ))}
                      </div>
                    )}

                    {t.answer.related.length > 0 && (
                      <div className="mt-3">
                        <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                          Related records
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {t.answer.related.map((r) => (
                            <span
                              key={r.id}
                              className="rounded-md border border-navy-600 bg-navy-850 px-2 py-1 text-[11px] text-ink-300"
                            >
                              <span className="text-brand-300">{r.type}</span> · {r.title}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {t.answer.citations.length > 0 && (
                      <div className="mt-3">
                        <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                          Citations
                        </div>
                        <div className="space-y-2">
                          {t.answer.citations.map((c, j) => (
                            <div
                              key={j}
                              className="rounded-lg border border-navy-700 bg-navy-850 p-3"
                            >
                              <div className="mb-1 flex items-center gap-2 text-xs text-ink-400">
                                <FileText size={13} className="text-brand-300" />
                                <span className="font-medium text-ink-300">
                                  {c.document_name}
                                </span>
                                {c.page != null && (
                                  <span className="ml-auto">page {c.page}</span>
                                )}
                              </div>
                              <blockquote className="border-l-2 border-brand-500/40 pl-3 text-xs leading-relaxed text-ink-300 italic">
                                “{c.excerpt}”
                              </blockquote>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* input */}
      <div className="sticky bottom-0 border-t border-navy-800 bg-navy-950/95 pt-3 pb-1 backdrop-blur">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            ask(question)
          }}
          className="flex items-center gap-2"
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about this project…"
            className="flex-1 rounded-xl border border-navy-600 bg-navy-850 px-4 py-3 text-sm text-ink-100 placeholder:text-ink-500 focus:border-brand-400 focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || !question.trim()}
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500 text-white transition hover:bg-brand-400 disabled:opacity-40"
          >
            <Send size={17} />
          </button>
        </form>
      </div>
    </div>
  )
}