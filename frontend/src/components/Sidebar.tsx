import { useEffect, useState } from 'react'
import { listJobs, deleteJob, type Job } from '../api/client'

interface Props {
  selectedId: string | null
  onSelect: (job: Job) => void
  onUploadClick: () => void
  onDelete: (jobId: string) => void
  refreshTick: number
}

const LANG_COLORS: Record<string, string> = {
  RPGLE:    '#4f8ef7',
  SQLRPGLE: '#4f8ef7',
  RPG:      '#4f8ef7',
  COBOL:    '#34c474',
  CLLE:     '#f5a623',
  CLP:      '#f5a623',
  DDS:      '#a78bfa',
  UNKNOWN:  '#555a72',
}

const STATUS_COLORS: Record<string, string> = {
  queued:     '#f5a623',
  processing: '#4f8ef7',
  completed:  '#34c474',
  failed:     '#f05353',
}

function langColor(lang: string | null) {
  return LANG_COLORS[lang ?? 'UNKNOWN'] ?? '#555a72'
}

// Group jobs by library — use filename extension first, fall back to detected language
function inferLibrary(lang: string | null, filename: string): string {
  const ext = filename.includes('.') ? filename.split('.').pop()!.toLowerCase() : ''
  switch (ext) {
    case 'rpgle': case 'sqlrpgle': case 'rpg': return 'QRPGLESRC'
    case 'cbl': case 'cob': case 'cobol':      return 'QCBLSRC'
    case 'clle': case 'clp':                   return 'QCLSRC'
    case 'dds': case 'pf': case 'lf':
    case 'prtf': case 'dspf':                  return 'QDDSSRC'
    default: break
  }
  // Fall back to detected language
  switch (lang) {
    case 'RPGLE': case 'SQLRPGLE': case 'RPG': return 'QRPGLESRC'
    case 'COBOL': return 'QCBLSRC'
    case 'CLLE':  case 'CLP': return 'QCLSRC'
    case 'DDS':   return 'QDDSSRC'
    default:      return 'QRPGLESRC'  // default most IBM i files to QRPGLESRC
  }
}

export default function Sidebar({ selectedId, onSelect, onDelete, refreshTick }: Omit<Props, 'onUploadClick'> & { onUploadClick?: () => void }) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [navItem, setNavItem] = useState<'documentation' | 'diagrams'>('documentation')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const handleDelete = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation()   // don't select the job when clicking delete
    if (!window.confirm('Delete this job and its files?')) return
    setDeletingId(jobId)
    try {
      await deleteJob(jobId)
      setJobs(prev => prev.filter(j => j.id !== jobId))
      onDelete(jobId)
    } catch {
      alert('Failed to delete job.')
    } finally {
      setDeletingId(null)
    }
  }

  useEffect(() => {
    let active = true
    const fetch_ = () => listJobs().then(d => { if (active) setJobs(d) }).catch(() => {})
    fetch_()
    const id = setInterval(fetch_, 3000)
    return () => { active = false; clearInterval(id) }
  }, [refreshTick])

  // Group by library — deduplicate by job id first
  const seen = new Set<string>()
  const uniqueJobs = jobs.filter(j => { if (seen.has(j.id)) return false; seen.add(j.id); return true })

  const byLib = uniqueJobs.reduce<Record<string, Job[]>>((acc, job) => {
    const lang     = job.files[0]?.language ?? null
    const filename = job.files[0]?.filename ?? ''
    const lib      = inferLibrary(lang, filename)
    ;(acc[lib] ??= []).push(job)
    return acc
  }, {})

  const completedCount = jobs.filter(j => j.status === 'completed').length
  const processingCount = jobs.filter(j => j.status === 'processing' || j.status === 'queued').length

  return (
    <div style={{ width: 'var(--sidebar-width)', background: 'var(--bg-surface)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', height: '100%', flexShrink: 0 }}>

      {/* Nav items */}
      <div style={{ padding: '0.5rem 0', flexShrink: 0 }}>
        {([
          { key: 'documentation', label: 'Documentation', badge: completedCount, badgeClass: 'badge-blue' },
          { key: 'diagrams',      label: 'Diagrams',      badge: completedCount, badgeClass: 'badge-blue' },
        ] as const).map(item => (
          <div key={item.key}
            onClick={() => setNavItem(item.key)}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '0.5rem 1rem', cursor: 'pointer',
              background: navItem === item.key ? 'var(--bg-hover)' : 'transparent',
              borderLeft: navItem === item.key ? '2px solid var(--accent-blue)' : '2px solid transparent',
              color: navItem === item.key ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontSize: '0.82rem', fontWeight: 500,
            }}>
            <span>{item.label}</span>
            {item.badge > 0 && <span className={`badge ${item.badgeClass}`}>{item.badge}</span>}
          </div>
        ))}

        {processingCount > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem 1rem', color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
            <span>Processing</span>
            <span className="badge badge-amber">{processingCount}</span>
          </div>
        )}
      </div>

      <div style={{ borderTop: '1px solid var(--border)', padding: '0.5rem 0', flex: 1, overflowY: 'auto' }}>
        <div style={{ padding: '0.4rem 1rem 0.25rem', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Source Files
        </div>

        {Object.keys(byLib).length === 0 && (
          <p style={{ padding: '0.5rem 1rem', color: 'var(--text-muted)', fontSize: '0.78rem' }}>No files yet.</p>
        )}

        {Object.entries(byLib).map(([lib, libJobs]) => (
          <div key={lib}>
            <div style={{ padding: '0.35rem 1rem', fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {lib}
            </div>
            {libJobs.map(job => {
              const f = job.files[0]
              if (!f) return null
              const selected = selectedId === job.id
              const hovered = hoveredId === job.id
              const deleting = deletingId === job.id
              return (
                <div key={job.id}
                  onClick={() => onSelect(job)}
                  onMouseEnter={() => setHoveredId(job.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                    padding: '0.3rem 0.5rem 0.3rem 1.25rem',
                    cursor: 'pointer',
                    background: selected ? 'var(--bg-hover)' : 'transparent',
                    borderLeft: selected ? '2px solid var(--accent-blue)' : '2px solid transparent',
                  }}>
                  <span className="status-dot" style={{ background: STATUS_COLORS[job.status] ?? '#555' }} />
                  <span className="status-dot" style={{ background: langColor(f.language), width: 8, height: 8 }} />
                  <span className="truncate" style={{ fontSize: '0.78rem', color: selected ? 'var(--text-primary)' : 'var(--text-secondary)', flex: 1 }}>
                    {f.filename}
                  </span>
                  {(hovered || deleting) && (
                    <button
                      onClick={e => handleDelete(e, job.id)}
                      disabled={deleting}
                      title="Delete job"
                      style={{
                        flexShrink: 0,
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--accent-red, #f05353)',
                        fontSize: '0.75rem', padding: '0 0.2rem',
                        opacity: deleting ? 0.5 : 1,
                      }}
                    >
                      {deleting ? '…' : '✕'}
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
