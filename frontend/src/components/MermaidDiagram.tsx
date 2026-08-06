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
  //    Must run BEFORE colon-label fix so the arrow token is clean first
  s = s.replace(/--([a-zA-Z][a-zA-Z0-9]*)-->/g, '-->|$1|')   // --read--> variant
  s = s.replace(/--([a-zA-Z][a-zA-Z0-9]*)->/g,  '-->|$1|')   // --read-> variant

  // 4. Fix subgraph curly-brace syntax line by line:
  //    "subgraph devOpsMenu{" → "subgraph devOpsMenu"
  //    A lone "}" line that closed a curly-brace subgraph → "end"
  s = s.split('\n').map(line => {
    // subgraph NAME{ or subgraph NAME { → strip the brace
    if (/^\s*subgraph\s+\S.*\{/.test(line)) {
      return line.replace(/\{.*$/, '').trimEnd()
    }
    // lone closing brace line → end
    if (/^\s*\}\s*$/.test(line)) {
      return line.replace('}', 'end')
    }
    return line
  }).join('\n')

  // 5. Fix trailing colon on node IDs: "main --> SQL_OPEN:" → "main --> SQL_OPEN"
  //    A bare word followed by colon at end of line or before newline is invalid
  s = s.replace(/([A-Za-z0-9_]+):\s*$/gm, '$1')

  // 6. Quote unquoted node labels that contain colons (invalid bare in Mermaid)
  //    Pattern: NODEID: Some Text  →  NODEID["Some Text"]
  //    Only applies inside arrow targets, e.g. "-->|label| NODEID: Text"
  s = s.replace(/(-->(?:\|[^|]*\|)?\s*)([A-Za-z0-9_]+):\s*([^\n]+)/g,
    (_m, arrow, id, label) => `${arrow}${id}["${label.trim()}"]`)

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
