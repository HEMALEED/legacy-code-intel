import type { JobStatus as JobStatusType } from '../api/client'

const CONFIG: Record<JobStatusType, { label: string; color: string }> = {
  queued:     { label: 'Queued',     color: '#f1c21b' },
  processing: { label: 'Processing', color: '#0f62fe' },
  completed:  { label: 'Completed',  color: '#24a148' },
  failed:     { label: 'Failed',     color: '#da1e28' },
}

export default function JobStatus({ status }: { status: JobStatusType }) {
  const { label, color } = CONFIG[status] ?? { label: status, color: '#8d8d8d' }
  return (
    <span style={{
      fontSize: '0.75rem',
      fontWeight: 600,
      color,
      background: color + '22',
      padding: '0.15rem 0.5rem',
      borderRadius: 12,
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  )
}
