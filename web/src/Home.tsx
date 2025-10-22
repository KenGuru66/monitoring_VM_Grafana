import { useState, useEffect } from 'react'
import { ExternalLink, Trash2, Download, Database, FileText, Loader, RefreshCw } from 'lucide-react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3000'

interface CSVJob {
  job_id: string
  target: 'csv' | 'perfmonkey'
  target_label: string
  serial_numbers: string[]
  status: string
  created_at: string
  updated_at: string
  filename: string
  files: FileInfo[]
  total_files: number
  total_size_mb: number
}

interface FileInfo {
  name: string
  size: number
  size_mb: number
  modified: string
  url: string
}

interface ArrayMetadata {
  sn: string
  scrape_interval: string | null
}

function Home() {
  const [arrays, setArrays] = useState<string[]>([])
  const [arraysMetadata, setArraysMetadata] = useState<ArrayMetadata[]>([])
  const [csvJobs, setCsvJobs] = useState<CSVJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)

    try {
      // Fetch arrays from VictoriaMetrics
      const arraysResponse = await fetch(`${API_URL}/api/arrays`)
      if (arraysResponse.ok) {
        const arraysData = await arraysResponse.json()
        setArrays(arraysData.arrays || [])
        // Get metadata (with scrape_interval)
        setArraysMetadata(arraysData.arrays_metadata || [])
      }

      // Fetch CSV jobs
      const csvJobsResponse = await fetch(`${API_URL}/api/csv-jobs`)
      if (csvJobsResponse.ok) {
        const csvJobsData = await csvJobsResponse.json()
        setCsvJobs(csvJobsData.csv_jobs || [])
      }
    } catch (err) {
      console.error('Error fetching data:', err)
      setError('Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleDeleteArray = async (sn: string) => {
    if (!confirm(`Are you sure you want to delete all data for array ${sn}?`)) {
      return
    }

    setDeleting(sn)
    try {
      const response = await fetch(`${API_URL}/api/arrays/${sn}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        setArrays(arrays.filter(a => a !== sn))
      } else {
        alert('Failed to delete array')
      }
    } catch (err) {
      console.error('Error deleting array:', err)
      alert('Failed to delete array')
    } finally {
      setDeleting(null)
    }
  }

  const handleDeleteCSVJob = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete all files for this job?')) {
      return
    }

    setDeleting(jobId)
    try {
      const response = await fetch(`${API_URL}/api/files/${jobId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        // Refresh CSV jobs
        await fetchData()
      } else {
        alert('Failed to delete files')
      }
    } catch (err) {
      console.error('Error deleting files:', err)
      alert('Failed to delete files')
    } finally {
      setDeleting(null)
    }
  }

  const openGrafana = (sn?: string, scrapeInterval?: string | null) => {
    const dashboard = `${GRAFANA_URL}/d/huawei-oceanstor-real/huawei-oceanstor-real-data`
    let url = dashboard

    if (sn) {
      url = `${dashboard}?var-SN=${sn}`
      // Add min_interval if available
      if (scrapeInterval) {
        url += `&var-min_interval=${scrapeInterval}`
      }
    }

    window.open(url, '_blank')
  }

  if (loading) {
    return (
      <div className="home-container">
        <div className="loading-state">
          <Loader className="animate-spin" size={48} />
          <p>Loading data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="home-container">
      <div className="home-header">
        <h1>Huawei Storage Performance Monitoring</h1>
        <button onClick={fetchData} className="refresh-button" title="Refresh">
          <RefreshCw size={20} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="error-message">
          <span>{error}</span>
        </div>
      )}

      {/* VictoriaMetrics Arrays Section */}
      <section className="data-section">
        <div className="section-header">
          <Database size={24} />
          <h2>Arrays in VictoriaMetrics ({arrays.length})</h2>
        </div>

        {arrays.length > 0 ? (
          <div className="arrays-grid">
            {arraysMetadata.map((arrayData: ArrayMetadata) => {
              const { sn, scrape_interval } = arrayData
              return (
                <div key={sn} className="array-card">
                  <div className="array-info">
                    <div className="array-sn">{sn}</div>
                    {scrape_interval && (
                      <div className="array-metadata">
                        <span className="interval-badge" title="Data collection interval">
                          ⏱️ {scrape_interval}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="array-actions">
                    <button
                      className="grafana-link-button"
                      onClick={() => openGrafana(sn, scrape_interval)}
                      title={`Open in Grafana${scrape_interval ? ` (interval: ${scrape_interval})` : ''}`}
                    >
                      <ExternalLink size={16} />
                      Grafana
                    </button>
                    <button
                      className="delete-icon-button"
                      onClick={() => handleDeleteArray(sn)}
                      disabled={deleting === sn}
                      title="Delete from VictoriaMetrics"
                    >
                      {deleting === sn ? (
                        <Loader className="animate-spin" size={16} />
                      ) : (
                        <Trash2 size={16} />
                      )}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="empty-state">
            <Database size={48} />
            <p>No arrays found in VictoriaMetrics</p>
            <small>Upload and process files with "Parse → Grafana" mode</small>
          </div>
        )}
      </section>

      {/* CSV Jobs Section */}
      <section className="data-section">
        <div className="section-header">
          <FileText size={24} />
          <h2>CSV Processing Jobs ({csvJobs.length})</h2>
        </div>

        {csvJobs.length > 0 ? (
          <div className="csv-jobs-list">
            {csvJobs.map((job) => (
              <div key={job.job_id} className="csv-job-card">
                <div className="csv-job-header">
                  <div className="csv-job-info">
                    <h3>
                      {job.serial_numbers.length > 0 ? (
                        job.serial_numbers.join(', ')
                      ) : (
                        <span className="text-muted">Unknown SN</span>
                      )}
                    </h3>
                    <div className="csv-job-meta">
                      <span className={`job-status status-${job.status}`}>{job.status}</span>
                      <span className="job-target">{job.target_label}</span>
                      <span className="job-filename">{job.filename}</span>
                    </div>
                    <div className="csv-job-stats">
                      <span>📁 {job.total_files} files</span>
                      <span>💾 {job.total_size_mb.toFixed(2)} MB</span>
                      <span>🕒 {new Date(job.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="csv-job-actions">
                    {job.status === 'done' && job.total_files > 0 && (
                      <button
                        className="delete-job-button"
                        onClick={() => handleDeleteCSVJob(job.job_id)}
                        disabled={deleting === job.job_id}
                        title="Delete all files"
                      >
                        {deleting === job.job_id ? (
                          <Loader className="animate-spin" size={16} />
                        ) : (
                          <>
                            <Trash2 size={16} />
                            Delete Files
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {job.status === 'done' && job.files.length > 0 && (
                  <div className="csv-files-table">
                    <table>
                      <thead>
                        <tr>
                          <th>Filename</th>
                          <th>Size</th>
                          <th>Modified</th>
                          <th>Download</th>
                        </tr>
                      </thead>
                      <tbody>
                        {job.files.map((file) => (
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
                )}

                {job.status === 'running' && (
                  <div className="job-processing">
                    <Loader className="animate-spin" size={24} />
                    <p>Processing files...</p>
                  </div>
                )}

                {job.status === 'error' && (
                  <div className="job-error">
                    <p>⚠️ Processing failed</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <FileText size={48} />
            <p>No CSV jobs found</p>
            <small>Upload and process files with "Parse → CSV" modes</small>
          </div>
        )}
      </section>
    </div>
  )
}

export default Home
