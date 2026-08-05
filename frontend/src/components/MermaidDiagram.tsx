import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  darkMode: true,
  suppressErrorRendering: true,   // stop the error toast popup
  themeVariables: {
    background: '#1a1d27',
    primaryColor: '#2a2f45',
    primaryTextColor: '#e8eaf0',
    lineColor: '#4f8ef7',
    edgeLabelBackground: '#22263a',
    clusterBkg: '#22263a',
  },
})

let _counter = 0

interface Props {
  source: string
}

// Try to auto-fix common LLM mistakes in Mermaid output
function sanitizeMermaid(src: string): string {
  return src
    .trim()
    // Remove accidental markdown fences
    .replace(/^```[a-z]*\n?/i, '')
    .replace(/```$/,            '')
    // Fix capitalised keywords that Mermaid requires lowercase
    .replace(/\bSubgraph\b/g,  'subgraph')
    .replace(/\bEnd\b/g,       'end')
    .replace(/\bGraph\b/g,     'graph')
    .replace(/\bFlowchart\b/g, 'flowchart')
    .replace(/\bSequenceDiagram\b/g, 'sequenceDiagram')
    // Fix arrow syntax: --> with label should be -->|label|
    .replace(/--([a-zA-Z])/g, '-- $1')
    .trim()
}

export default function MermaidDiagram({ source }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const id = useRef(`mermaid-${++_counter}`)

  useEffect(() => {
    if (!ref.current || !source.trim()) return
    setError(null)
    const clean = sanitizeMermaid(source)
    mermaid.render(id.current, clean)
      .then(({ svg }) => {
        if (ref.current) ref.current.innerHTML = svg
      })
      .catch((e) => {
        setError(String(e))
      })
    id.current = `mermaid-${++_counter}`
  }, [source])

  if (error) {
    return (
      <div style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <span style={{ color: 'var(--accent-amber)', fontSize: '0.82rem', fontWeight: 600 }}>
            ⚠ Diagram could not be rendered
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            — the AI generated invalid Mermaid syntax. Raw source below:
          </span>
        </div>
        <pre style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', background: 'var(--bg-raised)', padding: '0.75rem', borderRadius: 4 }}>
          {source}
        </pre>
      </div>
    )
  }

  return <div ref={ref} style={{ padding: '1rem', overflowX: 'auto' }} />
}
