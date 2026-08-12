import { useState, useEffect } from 'react'
import { getJob, getSourceFile, type Job } from '../api/client'
import DocView from './DocView'
import MermaidDiagram from './MermaidDiagram'

type Tab = 'documentation' | 'callflow' | 'dataflow' | 'source' | 'raw'

const isDev = new URLSearchParams(window.location.search).get('dev') === '1'

interface Props {
  jobId: string
}

export default function MainPanel({ jobId }: Props) {
  const [job, setJob]           = useState<Job | null>(null)
  const [tab, setTab]           = useState<Tab>('documentation')
  const [source, setSource]     = useState<string | null>(null)
  const [sourceLoading, setSourceLoading] = useState(false)

  // Poll job status
  useEffect(() => {
    setTab('documentation')
    setSource(null)
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

  // Fetch source when source tab is selected
  useEffect(() => {
    if (tab !== 'source' || !job?.files[0]) return
    if (source !== null) return   // already loaded
    setSourceLoading(true)
    getSourceFile(job.id, job.files[0].id)
      .then(text => setSource(text))
      .catch(() => setSource('// Could not load source file.'))
      .finally(() => setSourceLoading(false))
  }, [tab, job])

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
    { key: 'callflow',      label: '■ Call Flow' },
    { key: 'dataflow',      label: '◐ Data Flow' },
    { key: 'source',        label: '{ } Source' },
    ...(isDev ? [{ key: 'raw' as Tab, label: '≡ Raw JSON' }] : []),
  ]

  async function handleExport() {
    if (!docs) return

    const generatedAt = new Date().toLocaleString()
    const modeColor = (m: string) =>
      ({ READ: '#166534', WRITE: '#991b1b', UPDATE: '#92400e', DELETE: '#991b1b' }[m.toUpperCase()] ?? '#374151')
    const modeBg = (m: string) =>
      ({ READ: '#dcfce7', WRITE: '#fee2e2', UPDATE: '#fef3c7', DELETE: '#fee2e2' }[m.toUpperCase()] ?? '#f3f4f6')

    // Render Mermaid diagrams to SVG for embedding in the export
    async function renderDiagramSvg(source: string, id: string): Promise<string> {
      if (!source?.trim()) return ''
      try {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({ startOnLoad: false, theme: 'default' })
        const clean = source.trim()
          .replace(/^```[a-z]*\n?/i, '').replace(/```$/, '')
          .replace(/\bSubgraph\b/g, 'subgraph').replace(/\bEnd\b/g, 'end')
          .trim()
        const { svg } = await mermaid.render(id, clean)
        return svg
      } catch {
        return `<pre style="font-size:0.78rem;background:#f9fafb;padding:12px;border-radius:6px;white-space:pre-wrap">${source}</pre>`
      }
    }

    const [cfSvg, dfSvg] = await Promise.all([
      renderDiagramSvg(docs.call_flow_diagram ?? '', 'export-cf'),
      renderDiagramSvg(docs.data_flow_diagram ?? '', 'export-df'),
    ])

    const diagSection = (title: string, svgOrFallback: string) =>
      svgOrFallback
        ? `<h2>${title}</h2><div class="diagram-wrap">${svgOrFallback}</div>`
        : ''

    const rulesHtml = (docs.business_rules ?? []).map(br => `
      <div class="rule">
        <div class="rule-header">
          <strong>${br.rule}</strong>
          <span class="line-ref ${br.line_ref_verified === false ? 'unverified' : ''}"
                title="${br.line_ref_verified === false ? 'line reference could not be verified' : ''}">
            Line ${br.line_ref}${br.line_ref_verified === false ? ' ⚠' : ''}
          </span>
        </div>
        <p>${br.description}</p>
      </div>`).join('')

    const obsHtml = (docs.observations ?? []).map(o => `
      <div class="obs">
        <span class="badge ${o.severity === 'REVIEW' ? 'badge-review' : 'badge-info'}">${o.severity}</span>
        <span class="line-ref">Line ${o.line_ref}</span>
        <span class="obs-finding">${o.finding}</span>
      </div>`).join('')

    const filesHtml = (docs.files_used ?? []).map(f => `
      <tr>
        <td><code>${f.name}</code></td>
        <td><span style="color:${modeColor(f.mode)};background:${modeBg(f.mode)};padding:1px 6px;border-radius:3px;font-size:11px;font-weight:700">${f.mode.toUpperCase()}</span></td>
        <td>${f.description}</td>
      </tr>`).join('')

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>LegacyLens — ${filename}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system,"Segoe UI",system-ui,sans-serif; font-size: 14px;
         line-height: 1.6; color: #1f2328; background: #fff; padding: 40px; max-width: 960px; margin: 0 auto; }
  h1 { font-size: 1.6rem; font-weight: 800; margin-bottom: 4px; }
  h2 { font-size: 1rem; font-weight: 700; margin: 28px 0 10px;
       padding-bottom: 6px; border-bottom: 2px solid #e5e7eb; color: #374151; }
  .meta { font-size: 0.78rem; color: #6b7280; margin-bottom: 24px; }
  .badge { display:inline-block; font-size:11px; font-weight:700; padding:2px 6px; border-radius:3px; margin-right:6px; }
  .badge-ai { background:#dbeafe; color:#1e40af; }
  .badge-review { background:#fef3c7; color:#92400e; }
  .badge-info   { background:#f3f4f6; color:#6b7280; }
  table { width:100%; border-collapse:collapse; font-size:0.85rem; margin-bottom:8px; }
  th { text-align:left; padding:6px 10px; background:#f9fafb; border-bottom:2px solid #e5e7eb;
       font-size:0.75rem; text-transform:uppercase; letter-spacing:0.04em; color:#6b7280; }
  td { padding:6px 10px; border-bottom:1px solid #e5e7eb; vertical-align:top; }
  tr:last-child td { border-bottom:none; }
  code { font-family:"Cascadia Code","Fira Code",monospace; font-size:0.85em; background:#f3f4f6; padding:1px 4px; border-radius:3px; }
  .rule { border-left:3px solid #3b82f6; padding:6px 0 6px 12px; margin-bottom:10px; }
  .rule-header { display:flex; align-items:center; gap:10px; margin-bottom:2px; }
  .line-ref { font-size:0.75rem; color:#6b7280; background:#f3f4f6; padding:1px 6px; border-radius:3px; }
  .line-ref.unverified { color:#9ca3af; text-decoration:line-through; }
  .obs { display:flex; align-items:baseline; gap:8px; padding:5px 0; border-bottom:1px solid #f3f4f6; font-size:0.85rem; }
  .obs-finding { flex:1; }
  .summary-text { background:#f9fafb; border:1px solid #e5e7eb; border-radius:6px; padding:12px 16px; line-height:1.7; color:#374151; }
  .diagram-wrap { background:#f9fafb; border:1px solid #e5e7eb; border-radius:6px; padding:16px; overflow-x:auto; }
  .diagram-wrap svg { max-width:100%; height:auto; display:block; margin:0 auto; }
  .footer { margin-top:40px; padding-top:12px; border-top:1px solid #e5e7eb; font-size:0.72rem; color:#9ca3af; text-align:center; }
  @media print { body { padding:20px; } }
</style>
</head>
<body>
  <h1>${filename}</h1>
  <div class="meta">
    Language: <strong>${lang || '—'}</strong> &nbsp;·&nbsp;
    Size: <strong>${files[0] ? (files[0].size_bytes / 1024).toFixed(1) + ' KB' : '—'}</strong> &nbsp;·&nbsp;
    Generated: <strong>${generatedAt}</strong> &nbsp;·&nbsp;
    <span class="badge badge-ai">AI-GENERATED</span>
  </div>

  ${docs.summary ? `<h2>Summary</h2><div class="summary-text">${docs.summary}</div>` : ''}

  ${(docs.files_used ?? []).length > 0 ? `
  <h2>DB2 Tables / Files Used</h2>
  <table>
    <thead><tr><th>Name</th><th>Mode</th><th>Description</th></tr></thead>
    <tbody>${filesHtml}</tbody>
  </table>` : ''}

  ${(docs.business_rules ?? []).length > 0 ? `
  <h2>Business Rules</h2>${rulesHtml}` : ''}

  ${(docs.observations ?? []).length > 0 ? `
  <h2>Observations</h2>${obsHtml}` : ''}

  ${diagSection('Call Flow Diagram', cfSvg)}
  ${diagSection('Data Flow Diagram', dfSvg)}

  <div class="footer">Generated by LegacyLens &nbsp;·&nbsp; ${generatedAt}</div>
</body>
</html>`

    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}-documentation.html`
    a.click()
    URL.revokeObjectURL(url)
  }

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
        {docs && (
          <button
            onClick={handleExport}
            style={{ marginLeft: '0.5rem', fontSize: '0.72rem', padding: '0.2rem 0.6rem', borderRadius: 3, border: '1px solid var(--border)', background: 'var(--bg-base)', color: 'var(--text-secondary)', cursor: 'pointer' }}
          >
            ↓ Export
          </button>
        )}
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
              ? <MermaidDiagram
                  source={docs.call_flow_diagram}
                  fallback={!!(docs.raw_agent_output?.call_flow_fallback)}
                />
              : <p style={{ color: 'var(--text-muted)', padding: '2rem', textAlign: 'center' }}>No call flow diagram available.</p>
            }
          </div>
        )}

        {tab === 'dataflow' && (
          <div style={{ padding: '1rem' }}>
            {docs?.data_flow_diagram
              ? <MermaidDiagram
                  source={docs.data_flow_diagram}
                  fallback={!!(docs.raw_agent_output?.data_flow_fallback)}
                />
              : <p style={{ color: 'var(--text-muted)', padding: '2rem', textAlign: 'center' }}>No data flow diagram available.</p>
            }
          </div>
        )}

        {tab === 'source' && (
          <div style={{ display: 'flex', height: '100%' }}>
            {sourceLoading && (
              <p style={{ color: 'var(--text-muted)', padding: '2rem', margin: 0 }}>Loading source…</p>
            )}
            {!sourceLoading && source !== null && (
              <table style={{ borderCollapse: 'collapse', width: '100%', fontFamily: '"JetBrains Mono","Fira Code","Cascadia Code",monospace', fontSize: '0.78rem', lineHeight: 1.6 }}>
                <tbody>
                  {source.split('\n').map((line, i) => (
                    <tr key={i} style={{ verticalAlign: 'top' }}>
                      <td style={{ padding: '0 0.75rem', textAlign: 'right', color: 'var(--text-muted)', userSelect: 'none', borderRight: '1px solid var(--border)', minWidth: 48, background: 'var(--bg-surface)' }}>
                        {i + 1}
                      </td>
                      <td style={{ padding: '0 1rem', color: 'var(--text-secondary)', whiteSpace: 'pre', background: 'var(--bg-base)' }}>
                        {line || ' '}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
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
