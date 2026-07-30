import { useState, useRef, useEffect } from 'react'
import type { Job } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  text: string
}

interface Props {
  job: Job | null
}

const QUICK_ACTIONS = [
  'What does this program do?',
  'Which tables are updated?',
  'Show the call flow',
  'What are the key business rules?',
  'Any SQL risks?',
]

function buildContext(job: Job): string {
  const docs = job.docs
  if (!docs) return ''
  const parts: string[] = []
  if (docs.summary) parts.push(`SUMMARY:\n${docs.summary}`)
  if (docs.files_used?.length) {
    parts.push(`FILES USED:\n${docs.files_used.map(f => `  ${f.name} (${f.mode}) — ${f.description}`).join('\n')}`)
  }
  if (docs.business_rules?.length) {
    parts.push(`BUSINESS RULES:\n${docs.business_rules.map(r => `  [Line ${r.line_ref}] ${r.rule}: ${r.description}`).join('\n')}`)
  }
  return parts.join('\n\n')
}

export default function AiAssistant({ job }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const filename = job?.files[0]?.filename ?? null

  // Reset chat when job changes
  useEffect(() => {
    setMessages([])
  }, [job?.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage(text: string) {
    if (!text.trim() || !job?.docs) return
    const userMsg: Message = { role: 'user', text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Build prompt with context and send to backend /api/chat
    const context = buildContext(job)
    const prompt = `You are a legacy IBM i code analyst. Answer concisely based on this documentation context.\n\n${context}\n\nQuestion: ${text}`

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt }),
      })
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', text: data.reply ?? 'No response.' }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Could not reach the AI assistant.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-surface)', borderLeft: '1px solid var(--border)' }}>
      {/* Header */}
      <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--border)', background: 'var(--bg-raised)', flexShrink: 0 }}>
        <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)' }}>■ AI Assistant</div>
        {filename && (
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Context: {filename}
          </div>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {!job?.docs && (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', marginTop: '2rem' }}>
            Select a completed job to start chatting.
          </p>
        )}

        {job?.docs && messages.length === 0 && (
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.6 }}>
            Hi! I've read <strong style={{ color: 'var(--text-primary)' }}>{filename}</strong>. Ask me anything about the code.
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
            {m.text}
          </div>
        ))}

        {loading && (
          <div className="chat-bubble-ai" style={{ color: 'var(--text-muted)' }}>Thinking…</div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick actions */}
      {job?.docs && messages.length === 0 && (
        <div style={{ padding: '0.5rem 0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.4rem', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
          {QUICK_ACTIONS.map(q => (
            <button key={q} className="btn btn-ghost" style={{ fontSize: '0.72rem', padding: '0.2rem 0.5rem' }}
              onClick={() => sendMessage(q)}>
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ padding: '0.5rem 0.75rem', borderTop: '1px solid var(--border)', display: 'flex', gap: '0.4rem', flexShrink: 0 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage(input))}
          placeholder={job?.docs ? 'Ask about this code…' : 'Upload a file first…'}
          disabled={!job?.docs || loading}
          style={{
            flex: 1, background: 'var(--bg-raised)', border: '1px solid var(--border-light)',
            borderRadius: 4, color: 'var(--text-primary)', padding: '0.35rem 0.6rem',
            fontSize: '0.8rem', outline: 'none',
          }}
        />
        <button className="btn btn-primary" onClick={() => sendMessage(input)} disabled={!input.trim() || loading}>
          ↑
        </button>
      </div>
    </div>
  )
}
