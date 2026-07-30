import type { Job } from '../api/client'

interface Props { job: Job }

function ModeChip({ mode }: { mode: string }) {
  const colors: Record<string, [string, string]> = {
    READ:   ['#34c474', '#0f2a1a'],
    WRITE:  ['#f05353', '#2a0f0f'],
    UPDATE: ['#f5a623', '#2a1f0a'],
    DELETE: ['#f05353', '#2a0f0f'],
  }
  const [fg, bg] = colors[mode.toUpperCase()] ?? ['#8b90a8', '#22263a']
  return (
    <span style={{ color: fg, background: bg, padding: '0.1rem 0.45rem', borderRadius: 3, fontSize: '0.72rem', fontWeight: 700 }}>
      {mode.toUpperCase()}
    </span>
  )
}

export default function DocView({ job }: Props) {
  const { docs, error, status, files } = job
  const f = files[0]

  if (error) {
    return (
      <div style={{ padding: '1.5rem' }}>
        <div style={{ background: 'var(--accent-red-bg)', border: '1px solid var(--accent-red)', borderRadius: 6, padding: '1rem' }}>
          <strong style={{ color: 'var(--accent-red)' }}>Error:</strong>
          <span style={{ marginLeft: '0.5rem' }}>{error}</span>
        </div>
      </div>
    )
  }

  if (status === 'queued' || status === 'processing') {
    return (
      <div style={{ padding: '3rem', textAlign: 'center' }}>
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⏳</div>
        <p style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>Agent is running…</p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>This takes 20–90 s depending on file size.</p>
      </div>
    )
  }

  if (!docs) {
    return <div style={{ padding: '1.5rem', color: 'var(--text-muted)' }}>No documentation available.</div>
  }

  return (
    <div style={{ padding: '1rem 1.25rem', overflowY: 'auto', height: '100%' }}>

      {/* Program header */}
      <div className="section-card">
        <div className="section-card-header">
          <span className="section-card-title">▶ Program Header</span>
          <span style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span className="badge badge-blue">AI-GENERATED</span>
          </span>
        </div>
        <div className="section-card-body">
          <table className="data-table">
            <thead>
              <tr>
                <th>Program Name</th>
                <th>Type</th>
                <th>Language</th>
                <th>Size</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code>{f?.filename ?? '—'}</code></td>
                <td>{f?.language ?? '—'}</td>
                <td>{f?.language ?? '—'}</td>
                <td>{f ? `${(f.size_bytes / 1024).toFixed(1)} KB` : '—'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary */}
      {docs.summary && (
        <div className="section-card">
          <div className="section-card-header">
            <span className="section-card-title">📋 Summary</span>
            <span className="badge badge-blue">AI-GENERATED</span>
          </div>
          <div className="section-card-body">
            <p style={{ margin: 0, lineHeight: 1.7, color: 'var(--text-primary)', fontSize: '0.85rem' }}>{docs.summary}</p>
          </div>
        </div>
      )}

      {/* DB2 / Files used */}
      {docs.files_used && docs.files_used.length > 0 && (
        <div className="section-card">
          <div className="section-card-header">
            <span className="section-card-title">■ DB2 Tables / Files Used</span>
            <span className="badge badge-blue">AI-GENERATED</span>
          </div>
          <div style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Mode</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {docs.files_used.map((fu, i) => (
                  <tr key={i}>
                    <td><code>{fu.name}</code></td>
                    <td><ModeChip mode={fu.mode} /></td>
                    <td style={{ color: 'var(--text-secondary)' }}>{fu.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Business rules */}
      {docs.business_rules && docs.business_rules.length > 0 && (
        <div className="section-card">
          <div className="section-card-header">
            <span className="section-card-title">📐 Business Rules</span>
            <span className="badge badge-blue">AI-GENERATED</span>
          </div>
          <div className="section-card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {docs.business_rules.map((br, i) => (
              <div key={i} style={{ borderLeft: '2px solid var(--accent-blue)', paddingLeft: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <strong style={{ fontSize: '0.82rem' }}>{br.rule}</strong>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', background: 'var(--bg-raised)', padding: '0.1rem 0.4rem', borderRadius: 3 }}>
                    Line {br.line_ref}
                  </span>
                </div>
                <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>{br.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
