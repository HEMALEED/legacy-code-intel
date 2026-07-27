// Typed API client for the LCIP backend.
// All paths are relative so the Vite proxy forwards them to FastAPI.

export interface FileUsed {
  name: string
  mode: string
  description: string
}

export interface BusinessRule {
  rule: string
  line_ref: string
  description: string
}

export interface DocumentationResult {
  summary: string | null
  call_flow_diagram: string | null
  data_flow_diagram: string | null
  files_used: FileUsed[] | null
  business_rules: BusinessRule[] | null
}

export interface SourceFile {
  id: number
  filename: string
  language: string | null
  size_bytes: number
}

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed'

export interface Job {
  id: string
  status: JobStatus
  created_at: string
  updated_at: string
  error: string | null
  files: SourceFile[]
  docs: DocumentationResult | null
}

export interface JobCreated {
  job_id: string
  status: string
  files: string[]
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function uploadFiles(files: File[]): Promise<JobCreated> {
  const form = new FormData()
  for (const f of files) form.append('files', f)

  const res = await fetch('/api/jobs', { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Upload failed')
  }
  return res.json()
}

export async function listJobs(): Promise<Job[]> {
  const res = await fetch('/api/jobs')
  if (!res.ok) throw new Error('Failed to fetch jobs')
  return res.json()
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}`)
  if (!res.ok) throw new Error('Job not found')
  return res.json()
}
