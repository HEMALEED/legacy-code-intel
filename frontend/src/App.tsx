import { useState, useCallback } from 'react'
import UploadZone from './components/UploadZone'
import JobList from './components/JobList'
import JobDetail from './components/JobDetail'
import type { Job, JobCreated } from './api/client'

export default function App() {
  const [refreshTick, setRefreshTick] = useState(0)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  const handleJobCreated = useCallback((job: JobCreated) => {
    setRefreshTick((t) => t + 1)
    setSelectedJobId(job.job_id)
  }, [])

  const handleSelect = useCallback((job: Job) => {
    setSelectedJobId(job.id)
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 1200, margin: '0 auto', padding: '2rem 1.5rem' }}>
      {/* Header */}
      <header style={{ marginBottom: '2rem', borderBottom: '1px solid #e0e0e0', paddingBottom: '1rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>
          🏦 Legacy Code Intelligence Platform
        </h1>
        <p style={{ margin: '0.25rem 0 0', color: '#525252', fontSize: '0.9rem' }}>
          AI-powered documentation for RPG, COBOL, CLP, DDS and other IBM i source code
        </p>
      </header>

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '2rem', alignItems: 'start' }}>
        {/* Left column — upload + job list */}
        <div>
          <UploadZone onJobCreated={handleJobCreated} />
          <JobList
            refreshTick={refreshTick}
            onSelect={handleSelect}
            selectedId={selectedJobId}
          />
        </div>

        {/* Right column — job detail / documentation */}
        <div style={{
          background: '#fafafa',
          border: '1px solid #e0e0e0',
          borderRadius: 8,
          padding: '1.5rem',
          minHeight: 400,
        }}>
          {selectedJobId ? (
            <JobDetail jobId={selectedJobId} />
          ) : (
            <div style={{ textAlign: 'center', paddingTop: '3rem', color: '#8d8d8d' }}>
              <p style={{ fontSize: '1.1rem' }}>← Select a job to view documentation</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
