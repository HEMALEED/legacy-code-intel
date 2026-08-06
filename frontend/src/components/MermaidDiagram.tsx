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
  let s = src.trim()

  // 1. Strip markdown fences (opening fence may have a language tag,
  //    closing fence may be inline at end of last content line e.g. "main```")
  s = s.replace(/^```[a-z]*\r?\n?/i, '')  // opening fence
  s = s.replace(/```\s*$/, '')             // closing fence (inline or own line)

  // 2. Fix capitalised keywords Mermaid requires lowercase
  s = s.replace(/\bSubgraph\b/g, 'subgraph')
  s = s.replace(/\bEnd\b/g,      'end')
  s = s.replace(/\bGraph\b/g,    'graph')
  s = s.replace(/\bFlowchart\b/g,'flowchart')
  s = s.replace(/\bSequenceDiagram\b/g, 'sequenceDiagram')

  // 3. Fix invalid custom arrows: --read->, --write-> etc. → -->|read|
  s = s.replace(/--([a-zA-Z][a-zA-Z0-9]*)-->/g, '-->|$1|')   // --read--> variant
  s = s.replace(/--([a-zA-Z][a-zA-Z0-9]*)->/g,  '-->|$1|')   // --read-> variant

  // 4. Fix subgraph curly-brace syntax and lone closing braces — line by line
  s = s.split('\n').map(line => {
    if (/^\s*subgraph\s+\S.*\{/.test(line)) return line.replace(/\{.*$/, '').trimEnd()
    if (/^\s*\}\s*$/.test(line))            return line.replace('}', 'end')
    return line
  }).join('\n')

  // 5. Fix trailing colon on bare node IDs at end of line: "A --> SQL_OPEN:" → "A --> SQL_OPEN"
  s = s.replace(/([A-Za-z0-9_]+):\s*$/gm, '$1')

  // 6. Quote node labels inside [...] that contain a space or colon but are NOT already quoted.
  //    Covers:  A[Record: CHKOUT01]  →  A["Record: CHKOUT01"]
  //             F[R CHKOUT01]        →  F["R CHKOUT01"]
  //    Does NOT touch already-quoted labels like A["already fine"].
  s = s.replace(
    /([A-Za-z0-9_]+)\[([^\]"]+[\s:][^\]"]*)\]/g,
    (_m, nodeId, label) => `${nodeId}["${label.trim()}"]`
  )

  return s.trim()
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
