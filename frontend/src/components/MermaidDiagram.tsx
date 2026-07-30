import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  darkMode: true,
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

export default function MermaidDiagram({ source }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const id = useRef(`mermaid-${++_counter}`)

  useEffect(() => {
    if (!ref.current || !source.trim()) return
    setError(null)
    mermaid.render(id.current, source)
      .then(({ svg }) => {
        if (ref.current) ref.current.innerHTML = svg
      })
      .catch((e) => {
        setError(String(e))
      })
    // Increment id so re-renders use a fresh element
    id.current = `mermaid-${++_counter}`
  }, [source])

  if (error) {
    return (
      <div style={{ padding: '1rem' }}>
        <p style={{ color: 'var(--accent-amber)', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
          ⚠ Could not render diagram
        </p>
        <pre style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
          {source}
        </pre>
      </div>
    )
  }

  return <div ref={ref} style={{ padding: '1rem', overflowX: 'auto' }} />
}
