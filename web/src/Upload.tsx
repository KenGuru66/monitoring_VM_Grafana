import { useState, useEffect, useCallback } from 'react'
import { Upload as UploadIcon, CheckCircle, AlertCircle, Loader, ExternalLink, Download, Trash2, FileText, Database } from 'lucide-react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3000'

type ProcessingTarget = 'grafana' | 'csv' | 'perfmonkey'

interface JobStatus {
  job_id: string
  status: 'uploading' | 'pending' | 'running' | 'done' | 'error'
  progress: number
  message: string
  serial_numbers: string[]
  grafana_url?: string
  error?: string
  target?: ProcessingTarget
  files?: FileInfo[]
}

interface FileInfo {
  name: string
  size: number
  size_mb: number
  modified: string
  url: string
}

function Upload() {
  const [isDragging, setIsDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadSpeed, setUploadSpeed] = useState(0)
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showTargetSelection, setShowTargetSelection] = useState(false)
  const [fileList, setFileList] = useState<FileInfo[]>([])

  // Poll job status
  useEffect(() => {
    if (!jobId || uploading) return

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/status/${jobId}`)
        if (!response.ok) throw new Error('Failed to fetch status')

        const status: JobStatus = await response.json()
        setJobStatus(status)

        // Poll file list for CSV targets
        if ((status.target === 'csv' || status.target === 'perfmonkey') && status.status === 'running') {
          try {
            const filesResponse = await fetch(`${API_URL}/api/files/${jobId}`)
            if (filesResponse.ok) {
              const filesData = await filesResponse.json()
              setFileList(filesData.files || [])
            }
          } catch (err) {
            console.error('Error fetching files:', err)
          }
        }

        if (status.status === 'done') {
          // Final fetch of files for CSV targets
          if (status.target === 'csv' || status.target === 'perfmonkey') {
            try {
              const filesResponse = await fetch(`${API_URL}/api/files/${jobId}`)
              if (filesResponse.ok) {
                const filesData = await filesResponse.json()
                setFileList(filesData.files || [])
              }
            } catch (err) {
              console.error('Error fetching files:', err)
            }
          }
          clearInterval(pollInterval)
        }

        if (status.status === 'error') {
          clearInterval(pollInterval)
        }
      } catch (err) {
        console.error('Error polling status:', err)
      }
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [jobId, uploading])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.name.endsWith('.zip')) {
      setFile(droppedFile)
      setError(null)
    } else {
      setError('Please upload a .zip file')
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile && selectedFile.name.endsWith('.zip')) {
      setFile(selectedFile)
      setError(null)
    } else {
      setError('Please upload a .zip file')
    }
  }, [])

  const handleUpload = async (target: ProcessingTarget) => {
    if (!file) return

    setUploading(true)
    setError(null)
    setJobId(null)
    setJobStatus(null)
    setUploadProgress(0)
    setUploadSpeed(0)
    setFileList([])
    setShowTargetSelection(false)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('target', target)

    try {
      const xhr = new XMLHttpRequest()
      let uploadStartTime = Date.now() / 1000

      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100
          setUploadProgress(percentComplete)

          // Calculate speed (simplified)
          const elapsed = Date.now() / 1000 - uploadStartTime
          const speed = e.loaded / (1024 * 1024) / (elapsed || 1)
          setUploadSpeed(speed)
        }
      })

      // Handle completion
      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          const data = JSON.parse(xhr.responseText)
          setJobId(data.job_id)
          setJobStatus({
            job_id: data.job_id,
            status: 'pending',
            progress: 0,
            message: data.message || 'Upload successful, processing started...',
            serial_numbers: data.serial_numbers || [],
            target: target,
          })
        } else {
          const errorData = JSON.parse(xhr.responseText)
          throw new Error(errorData.detail || 'Upload failed')
        }
        setUploading(false)
      })

      // Handle errors
      xhr.addEventListener('error', () => {
        setError('Upload failed - network error')
        setUploading(false)
      })

      uploadStartTime = Date.now() / 1000
      xhr.open('POST', `${API_URL}/api/upload`)
      xhr.send(formData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
    }
  }

  const handleShowTargetSelection = () => {
    if (!file) return
    setShowTargetSelection(true)
  }

  const handleDeleteFiles = async () => {
    if (!jobId) return

    try {
      const response = await fetch(`${API_URL}/api/files/${jobId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        setFileList([])
        if (jobStatus) {
          setJobStatus({ ...jobStatus, files: [] })
        }
      }
    } catch (err) {
      console.error('Error deleting files:', err)
      setError('Failed to delete files')
    }
  }

  const handleReset = () => {
    setFile(null)
    setJobId(null)
    setJobStatus(null)
    setError(null)
    setUploadProgress(0)
    setUploadSpeed(0)
    setShowTargetSelection(false)
    setFileList([])
  }

  const getStatusIcon = () => {
    if (uploading) {
      return <UploadIcon className="animate-spin" size={48} color="#3b82f6" />
    }

    if (!jobStatus) return null

    switch (jobStatus.status) {
      case 'pending':
      case 'running':
        return <Loader className="animate-spin" size={48} />
      case 'done':
        return <CheckCircle size={48} color="#22c55e" />
      case 'error':
        return <AlertCircle size={48} color="#ef4444" />
      default:
        return null
    }
  }

  const getStatusColor = () => {
    if (uploading) return '#3b82f6'
    if (!jobStatus) return '#3b82f6'

    switch (jobStatus.status) {
      case 'pending':
        return '#f59e0b'
      case 'running':
        return '#3b82f6'
      case 'done':
        return '#22c55e'
      case 'error':
        return '#ef4444'
      default:
        return '#3b82f6'
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="upload-container">
      {!jobId && !uploading ? (
        <div className="upload-section">
          <div
            className={`dropzone ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <UploadIcon size={48} />
            <h2>Drag & Drop your .zip file here</h2>
            <p>or</p>
            <label className="file-input-label">
              <input
                type="file"
                accept=".zip"
                onChange={handleFileSelect}
                className="file-input"
              />
              <span>Browse Files</span>
            </label>

            {file && (
              <div className="file-info">
                <p className="file-name">📦 {file.name}</p>
                <p className="file-size">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
              </div>
            )}
          </div>

          {error && (
            <div className="error-message">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}

          {file && !showTargetSelection && (
            <button className="upload-button" onClick={handleShowTargetSelection}>
              Choose Processing Mode →
            </button>
          )}

          {file && showTargetSelection && (
            <div className="target-selection">
              <h3>Select Processing Mode:</h3>
              <div className="target-buttons">
                <button
                  className="target-button grafana"
                  onClick={() => handleUpload('grafana')}
                >
                  <Database size={24} />
                  <span>Parse → Grafana</span>
                  <small>Stream to VictoriaMetrics</small>
                </button>

                <button
                  className="target-button csv"
                  onClick={() => handleUpload('csv')}
                >
                  <FileText size={24} />
                  <span>Parse → CSV (Wide)</span>
                  <small>Download CSV files (wide format)</small>
                </button>

                <button
                  className="target-button perfmonkey"
                  onClick={() => handleUpload('perfmonkey')}
                >
                  <FileText size={24} />
                  <span>Parse → CSV (Perfmonkey)</span>
                  <small>Download CSV files (perfmonkey format)</small>
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="status-section">
          <div className="status-icon">
            {getStatusIcon()}
          </div>

          <h2 className="status-title">
            {uploading ? 'Uploading...' : jobStatus?.status === 'done' ? 'Processing Complete!' : 'Processing...'}
          </h2>

          {uploading ? (
            <>
              <div className="progress-container">
                <div className="progress-bar-bg">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${uploadProgress}%`,
                      backgroundColor: '#3b82f6',
                    }}
                  />
                </div>
                <div className="progress-text">
                  <span className="progress-percent">{uploadProgress.toFixed(1)}%</span>
                  <span className="progress-status">Uploading</span>
                </div>
              </div>

              <div className="upload-stats">
                <p>📊 Upload Speed: {uploadSpeed.toFixed(2)} MB/s</p>
                {file && (
                  <p>📁 Size: {formatBytes(file.size)}</p>
                )}
              </div>
            </>
          ) : (
            <>
              {jobStatus?.serial_numbers && jobStatus.serial_numbers.length > 0 && (
                <div className="serial-numbers">
                  <p className="serial-label">Detected Serial Numbers:</p>
                  <div className="serial-list">
                    {jobStatus.serial_numbers.map((sn) => (
                      <span key={sn} className="serial-badge">{sn}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="progress-container">
                <div className="progress-bar-bg">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${jobStatus?.progress || 0}%`,
                      backgroundColor: getStatusColor(),
                    }}
                  />
                </div>
                <div className="progress-text">
                  <span className="progress-percent">{jobStatus?.progress || 0}%</span>
                  <span className="progress-status">{jobStatus?.status}</span>
                </div>
              </div>

              <p className="status-message">{jobStatus?.message}</p>

              {jobStatus?.error && (
                <div className="error-message">
                  <AlertCircle size={20} />
                  <span>{jobStatus.error}</span>
                </div>
              )}

              {jobStatus?.status === 'done' && (
                <>
                  {jobStatus.target === 'grafana' && (
                    <div className="action-buttons">
                      <a
                        href={jobStatus.grafana_url || GRAFANA_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="grafana-button"
                      >
                        <ExternalLink size={20} />
                        Open in Grafana
                      </a>
                      <button onClick={handleReset} className="reset-button">
                        Upload Another File
                      </button>
                    </div>
                  )}

                  {(jobStatus.target === 'csv' || jobStatus.target === 'perfmonkey') && (
                    <div className="csv-results">
                      <h3>📁 Generated Files ({fileList.length})</h3>

                      {fileList.length > 0 ? (
                        <>
                          <div className="files-table">
                            <table>
                              <thead>
                                <tr>
                                  <th>Filename</th>
                                  <th>Size</th>
                                  <th>Modified</th>
                                  <th>Action</th>
                                </tr>
                              </thead>
                              <tbody>
                                {fileList.map((file) => (
                                  <tr key={file.name}>
                                    <td className="file-name">{file.name}</td>
                                    <td>{file.size_mb.toFixed(2)} MB</td>
                                    <td>{new Date(file.modified).toLocaleString()}</td>
                                    <td>
                                      <a
                                        href={`${API_URL}${file.url}`}
                                        download
                                        className="download-link"
                                      >
                                        <Download size={16} />
                                        Download
                                      </a>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>

                          <div className="file-actions">
                            <button onClick={handleDeleteFiles} className="delete-button">
                              <Trash2 size={16} />
                              Delete All Files
                            </button>
                            <button onClick={handleReset} className="reset-button">
                              Upload Another File
                            </button>
                          </div>
                        </>
                      ) : (
                        <div className="files-waiting">
                          <Loader className="animate-spin" size={32} />
                          <p>Files are being compressed, please wait...</p>
                          <small>This may take up to 30 seconds</small>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

              {jobStatus?.status === 'error' && (
                <button onClick={handleReset} className="reset-button">
                  Try Again
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default Upload
