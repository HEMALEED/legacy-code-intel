import { useEffect, useState } from 'react'
import { getJob, type Job } from '../api/client'

interface Props {
  jobId: string
}

export default function JobDetail({ jobId }: Props) {
  const [job, setJob] = useState<Job | null>(null)
  const [showRaw, setShowRaw] = useState(false)

  useEffect(() => {
    let active = true
    const poll = () =>
      getJob(jobId).then((j) => {
        if (!active) return
        setJob(j)
        // Stop polling once terminal
        if (j.status === 'completed' || j.status === 'failed') {
          clearInterval(id)
        }
      }).catch(() => {})

    poll()
    const id = setInterval(poll, 2000)
    return () => { active = false; clearInterval(id) }
  }, [jobId])

  if (!job) return <p style={{ color: '#525252' }}>Loading…</p>

  const { docs, error, status, files } = job

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>
        {files.map((f) => f.filename).join(', ')}
        {' '}
        <span style={{
          fontSize: '0.8rem',
          fontWeight: 400,
          color: status === 'completed' ? '#24a148' : status === 'failed' ? '#da1e28' : '#0f62fe',
        }}>
          [{status}]
        </span>
      </h2>

      {/* Language badge */}
      {files[0]?.language && (
        <span style={{
          display: 'inline-block',
          background: '#e0e0e0',
          borderRadius: 4,
          padding: '0.1rem 0.5rem',
          fontSize: '0.8rem',
          marginBottom: '1rem',
        }}>
          {files[0].language}
        </span>
      )}

      {/* Error */}
      {error && (
        <div style={{ background: '#fff1f1', border: '1px solid #da1e28', borderRadius: 6, padding: '1rem', marginBottom: '1rem' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Processing spinner */}
      {(status === 'queued' || status === 'processing') && !docs && (
        <p style={{ color: '#0f62fe' }}>
          ⏳ Agent is running… this takes 20–60 s depending on file size.
        </p>
      )}

      {/* Documentation result */}
      {docs && (
        <div>
          {/* Summary */}
          {docs.summary && (
            <section style={sectionStyle}>
              <h3 style={h3Style}>📋 Summary</h3>
              <p style={{ margin: 0, lineHeight: 1.6 }}>{docs.summary}</p>
            </section>
          )}

          {/* Files used */}
          {docs.files_used && docs.files_used.length > 0 && (
            <section style={sectionStyle}>
              <h3 style={h3Style}>📂 Files / Tables Used</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr>
                    {['Name', 'Mode', 'Description'].map((h) => (
                      <th key={h} style={thStyle}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {docs.files_used.map((fu, i) => (
                    <tr key={i} style={{ background: i % 2 === 0 ? '#f9f9f9' : '#fff' }}>
                      <td style={tdStyle}><code>{fu.name}</code></td>
                      <td style={{ ...tdStyle, color: modeColor(fu.mode), fontWeight: 600 }}>{fu.mode}</td>
                      <td style={tdStyle}>{fu.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {/* Business rules */}
          {docs.business_rules && docs.business_rules.length > 0 && (
            <section style={sectionStyle}>
              <h3 style={h3Style}>📐 Business Rules</h3>
              {docs.business_rules.map((br, i) => (
                <div key={i} style={{ borderLeft: '3px solid #0f62fe', paddingLeft: '0.75rem', marginBottom: '0.75rem' }}>
                  <strong>{br.rule}</strong>
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: '#525252' }}>
                    Line {br.line_ref}
                  </span>
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.9rem' }}>{br.description}</p>
                </div>
              ))}
            </section>
          )}

          {/* Diagrams — raw Mermaid source (Track 2 will render these) */}
          {(docs.call_flow_diagram || docs.data_flow_diagram) && (
            <section style={sectionStyle}>
              <h3 style={h3Style}>🔀 Diagrams <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>(Track 2 will render these visually)</span></h3>
              {docs.call_flow_diagram && (
                <details style={{ marginBottom: '0.5rem' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '0.9rem' }}>Call Flow (Mermaid source)</summary>
                  <pre style={preStyle}>{docs.call_flow_diagram}</pre>
                </details>
              )}
              {docs.data_flow_diagram && (
                <details>
                  <summary style={{ cursor: 'pointer', fontSize: '0.9rem' }}>Data Flow (Mermaid source)</summary>
                  <pre style={preStyle}>{docs.data_flow_diagram}</pre>
                </details>
              )}
            </section>
          )}

          {/* Raw JSON toggle */}
          <details style={{ marginTop: '1rem' }}>
            <summary
              style={{ cursor: 'pointer', fontSize: '0.85rem', color: '#525252' }}
              onClick={() => setShowRaw((x) => !x)}
            >
              {showRaw ? 'Hide' : 'Show'} raw agent output
            </summary>
            {showRaw && (
              <pre style={{ ...preStyle, maxHeight: 400, overflow: 'auto' }}>
                {JSON.stringify(docs, null, 2)}
              </pre>
            )}
          </details>
        </div>
      )}
    </div>
  )
}

// ── Local helpers ─────────────────────────────────────────────────────────────

function modeColor(mode: string): string {
  switch (mode.toUpperCase()) {
    case 'WRITE':  return '#da1e28'
    case 'READ':   return '#24a148'
    case 'UPDATE': return '#f1c21b'
    case 'DELETE': return '#da1e28'
    default:       return '#525252'
  }
}

// ── Inline styles ─────────────────────────────────────────────────────────────

const sectionStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
}

const h3Style: React.CSSProperties = {
  margin: '0 0 0.75rem',
  fontSize: '1rem',
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '0.4rem 0.75rem',
  background: '#e0e0e0',
  borderBottom: '1px solid #c6c6c6',
}

const tdStyle: React.CSSProperties = {
  padding: '0.4rem 0.75rem',
  borderBottom: '1px solid #e8e8e8',
  verticalAlign: 'top',
}

const preStyle: React.CSSProperties = {
  background: '#1c1c1c',
  color: '#f4f4f4',
  padding: '1rem',
  borderRadius: 6,
  fontSize: '0.8rem',
  overflow: 'auto',
  margin: '0.5rem 0 0',
}
