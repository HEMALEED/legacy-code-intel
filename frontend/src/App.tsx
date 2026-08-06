import { useState, useCallback, useRef } from 'react'
import Sidebar from './components/Sidebar'
import MainPanel from './components/MainPanel'
import AiAssistant from './components/AiAssistant'
import { uploadFiles, type Job, type JobCreated } from './api/client'

export default function App() {
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [showAssistant, setShowAssistant] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleJobCreated = useCallback((job: JobCreated) => {
    setRefreshTick(t => t + 1)
    // Auto-select newly created job by setting a stub — sidebar polling will fill it in
    setSelectedJob({ id: job.job_id, status: 'queued', created_at: '', updated_at: '', error: null, files: [], docs: null })
  }, [])

  const handleUpload = useCallback(async (files: File[]) => {
    if (!files.length) return
    setUploadError(null)
    setUploading(true)
    try {
      const job = await uploadFiles(files)
      handleJobCreated(job)
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [handleJobCreated])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    handleUpload(Array.from(e.dataTransfer.files))
  }, [handleUpload])

  return (
    <div
      style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}
      onDragOver={e => e.preventDefault()}
      onDrop={onDrop}
    >
      {/* ── Top bar ─────────────────────────────────────────────────── */}
      <header style={{
        height: 'var(--topbar-height)',
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center',
        padding: '0 1rem', gap: '1rem', flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            LegacyLens
          </span>
          <span style={{ fontSize: '0.68rem', background: 'var(--bg-raised)', color: 'var(--text-muted)', padding: '0.1rem 0.45rem', borderRadius: 3, fontWeight: 600 }}>
            AS/400 · IBM i
          </span>
        </div>

        {/* Workspace */}
        <div style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'var(--bg-raised)', padding: '0.2rem 0.75rem', borderRadius: 4, border: '1px solid var(--border)' }}>
          ● DEV Workspace
        </div>

        <div style={{ flex: 1 }} />

        {/* Upload error */}
        {uploadError && (
          <span style={{ fontSize: '0.75rem', color: 'var(--accent-red)' }}>{uploadError}</span>
        )}

        {/* AI Assistant toggle */}
        <button
          className="btn btn-ghost"
          onClick={() => setShowAssistant(v => !v)}
          title={showAssistant ? 'Hide AI Assistant' : 'Show AI Assistant'}
          style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem', opacity: showAssistant ? 1 : 0.5 }}
        >
          ■ AI {showAssistant ? 'ON' : 'OFF'}
        </button>

        {/* Upload button */}
        <input
          ref={fileInputRef}
          type="file" multiple
          accept=".rpg,.rpgle,.sqlrpgle,.cbl,.cob,.cobol,.clp,.clle,.dds,.pf,.lf,.prtf,.dspf,.zip"
          style={{ display: 'none' }}
          onChange={e => handleUpload(Array.from(e.target.files ?? []))}
        />
        <button
          className="btn btn-primary"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? '⏳ Uploading…' : '+ Upload Source'}
        </button>

        {/* Avatar */}
        <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 700 }}>
          NP
        </div>
      </header>

      {/* ── Body ────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Sidebar */}
        <Sidebar
          selectedId={selectedJob?.id ?? null}
          onSelect={setSelectedJob}
          onUploadClick={() => fileInputRef.current?.click()}
          onDelete={(jobId) => { if (selectedJob?.id === jobId) setSelectedJob(null) }}
          refreshTick={refreshTick}
        />

        {/* Main panel */}
        {selectedJob?.id
          ? <MainPanel jobId={selectedJob.id} />
          : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: '2.5rem' }}>⬡</div>
              <p style={{ margin: 0, fontWeight: 600, fontSize: '1rem', color: 'var(--text-secondary)' }}>LegacyLens</p>
              <p style={{ margin: 0, fontSize: '0.85rem' }}>Upload an RPG, COBOL, CLP or DDS source file to generate documentation.</p>
              <button className="btn btn-primary" style={{ marginTop: '0.5rem' }} onClick={() => fileInputRef.current?.click()}>
                + Upload Source
              </button>
            </div>
          )
        }

        {/* AI Assistant panel */}
        {showAssistant && (
          <div style={{ width: 'var(--assistant-width)', flexShrink: 0 }}>
            <AiAssistant job={selectedJob} />
          </div>
        )}
      </div>

      {/* ── Status bar ──────────────────────────────────────────────── */}
      <div style={{
        height: 'var(--statusbar-height)',
        background: 'var(--bg-raised)',
        borderTop: '1px solid var(--border)',
        display: 'flex', alignItems: 'center',
        padding: '0 1rem', gap: '1.5rem',
        fontSize: '0.72rem', color: 'var(--text-muted)', flexShrink: 0,
      }}>
        <span style={{ color: 'var(--accent-green)' }}>● Connected</span>
        {selectedJob && selectedJob.files[0] && (
          <>
            <span>▶ {selectedJob.files[0].filename}</span>
            {selectedJob.files[0].language && (
              <span>{selectedJob.files[0].language}</span>
            )}
          </>
        )}
        <div style={{ flex: 1 }} />
        <span>LegacyLens v2.0</span>
      </div>
    </div>
  )
}
