import { useCallback, useState } from 'react'
import { uploadFiles, type JobCreated } from '../api/client'

interface Props {
  onJobCreated: (job: JobCreated) => void
}

export default function UploadZone({ onJobCreated }: Props) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFiles = useCallback(
    async (files: File[]) => {
      if (!files.length) return
      setError(null)
      setUploading(true)
      try {
        const job = await uploadFiles(files)
        onJobCreated(job)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload failed')
      } finally {
        setUploading(false)
      }
    },
    [onJobCreated],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      handleFiles(Array.from(e.dataTransfer.files))
    },
    [handleFiles],
  )

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragging ? '#0f62fe' : '#8d8d8d'}`,
          borderRadius: 8,
          padding: '3rem 2rem',
          textAlign: 'center',
          background: dragging ? '#edf5ff' : '#f4f4f4',
          cursor: 'pointer',
          transition: 'all 0.15s',
        }}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          multiple
          accept=".rpg,.rpgle,.sqlrpgle,.cbl,.cob,.cobol,.clp,.clle,.dds,.pf,.lf,.prtf,.dspf,.zip"
          style={{ display: 'none' }}
          onChange={(e) => handleFiles(Array.from(e.target.files ?? []))}
        />
        {uploading ? (
          <p style={{ margin: 0, color: '#0f62fe' }}>Uploading…</p>
        ) : (
          <>
            <p style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
              Drop source files or a ZIP here
            </p>
            <p style={{ margin: '0.5rem 0 0', color: '#525252', fontSize: '0.9rem' }}>
              Supported: RPG, RPGLE, COBOL, CLP, CLLE, DDS, PF, LF — or a .zip of any of these
            </p>
          </>
        )}
      </div>
      {error && (
        <p style={{ color: '#da1e28', marginTop: '0.5rem' }}>{error}</p>
      )}
    </div>
  )
}
