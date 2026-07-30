import { useState, useEffect } from 'react'
import { getJob, type Job } from '../api/client'
import DocView from './DocView'
import MermaidDiagram from './MermaidDiagram'

type Tab = 'documentation' | 'callflow' | 'dataflow' | 'raw'

interface Props { jobId: string }

export default function MainPanel({ jobId }: Props) {
  const [job, setJob] = useState<Job | null>(null)
  const [tab, setTab] = useState<Tab>('documentation')

  useEffect(() => {
    setTab('documentation')
    let active = true
    const poll = () =>
      getJob(jobId).then(j => {
        if (!active) return
        setJob(j)
        if (j.status === 'completed' || j.status === 'failed') clearInterval(id)
      }).catch(() => {})
    poll()
    const id = setInterval(poll, 2500)
    return () => { active = false; clearInterval(id) }
  }, [jobId])

  if (!job) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        Loading…
      </div>
    )
  }

  const { docs, files } = job
  const filename = files[0]?.filename ?? 'Unknown'
  const lang = files[0]?.language ?? ''

  const tabs: { key: Tab; label: string }[] = [
    { key: 'documentation', label: '▶ Documentation' },
    { key: 'callflow',      label: '■ Call Flow Diagram' },
    { key: 'dataflow',      label: '◐ Data Flow' },
    { key: 'raw',           label: '≡ Raw Source' },
  ]

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, height: '100%' }}>
      {/* File title bar */}
      <div style={{ padding: '0.5rem 1rem', borderBottom: '1px solid var(--border)', background: 'var(--bg-raised)', display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
        <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{filename}</span>
        {lang && (
          <span style={{ fontSize: '0.72rem', background: 'var(--bg-hover)', color: 'var(--accent-blue)', padding: '0.1rem 0.5rem', borderRadius: 3, fontWeight: 600 }}>
            {lang}
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: job.status === 'completed' ? 'var(--accent-green)' : job.status === 'failed' ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
          ● {job.status.toUpperCase()}
        </span>
      </div>

      {/* Tab bar */}
      <div className="tab-bar">
        {tabs.map(t => (
          <div key={t.key} className={`tab ${tab === t.key ? 'active' : ''}`} onClick={() => setTab(t.key)}>
            {t.label}
          </div>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {tab === 'documentation' && <DocView job={job} />}

        {tab === 'callflow' && (
          <div style={{ padding: '1rem' }}>
            {docs?.call_flow_diagram
              ? <MermaidDiagram source={docs.call_flow_diagram} />
              : <p style={{ color: 'var(--text-muted)', padding: '2rem', textAlign: 'center' }}>No call flow diagram available.</p>
            }
          </div>
        )}

        {tab === 'dataflow' && (
          <div style={{ padding: '1rem' }}>
            {docs?.data_flow_diagram
              ? <MermaidDiagram source={docs.data_flow_diagram} />
              : <p style={{ color: 'var(--text-muted)', padding: '2rem', textAlign: 'center' }}>No data flow diagram available.</p>
            }
          </div>
        )}

        {tab === 'raw' && (
          <pre style={{ margin: 0, padding: '1rem', fontSize: '0.78rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {JSON.stringify(docs, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
