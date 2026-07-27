import { useEffect, useState } from 'react'
import { listJobs, type Job } from '../api/client'
import JobStatus from './JobStatus'

interface Props {
  refreshTick: number           // increment from parent to force a re-fetch
  onSelect: (job: Job) => void
  selectedId: string | null
}

const STATUS_COLORS: Record<string, string> = {
  queued:     '#f1c21b',
  processing: '#0f62fe',
  completed:  '#24a148',
  failed:     '#da1e28',
}

export default function JobList({ refreshTick, onSelect, selectedId }: Props) {
  const [jobs, setJobs] = useState<Job[]>([])

  useEffect(() => {
    let active = true
    const fetch_ = () =>
      listJobs().then((data) => { if (active) setJobs(data) }).catch(() => {})

    fetch_()
    // Poll every 3 s while any job is in-progress
    const id = setInterval(() => {
      fetch_()
    }, 3000)
    return () => { active = false; clearInterval(id) }
  }, [refreshTick])

  if (!jobs.length) {
    return <p style={{ color: '#525252' }}>No jobs yet. Upload a file to get started.</p>
  }

  return (
    <div>
      <h2 style={{ margin: '0 0 1rem' }}>Jobs</h2>
      {jobs.map((job) => (
        <div
          key={job.id}
          onClick={() => onSelect(job)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.75rem 1rem',
            marginBottom: '0.5rem',
            borderRadius: 6,
            background: selectedId === job.id ? '#edf5ff' : '#f4f4f4',
            border: selectedId === job.id ? '1.5px solid #0f62fe' : '1.5px solid transparent',
            cursor: 'pointer',
          }}
        >
          {/* Status dot */}
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: STATUS_COLORS[job.status] ?? '#8d8d8d',
              flexShrink: 0,
            }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {job.files.map((f) => f.filename).join(', ')}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#525252' }}>
              {new Date(job.created_at).toLocaleString()} · {job.status}
            </div>
          </div>
          <JobStatus status={job.status} />
        </div>
      ))}
    </div>
  )
}
