import { useState, useEffect, useCallback, useRef } from 'react'
import { CheckCircle, AlertCircle, Loader, ExternalLink, Download, Trash2, FileText, Database, X, Files, PlayCircle } from 'lucide-react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type ProcessingTarget = 'grafana' | 'csv' | 'perfmonkey'
// pending - ждёт старта
// uploading - загружается на сервер
// queued - загружен, ждёт обработки в очереди
// running - обрабатывается
// done - готово
// error - ошибка
type QueueItemStatus = 'pending' | 'uploading' | 'queued' | 'running' | 'done' | 'error'

interface FileInfo {
  name: string
  size: number
  size_mb: number
  modified: string
  url: string
}

interface QueueItem {
  id: string
  file: File
  status: QueueItemStatus
  uploadProgress: number
  processingProgress: number
  message: string
  jobId?: string
  serialNumbers?: string[]
  grafanaUrl?: string
  error?: string
  files?: FileInfo[]
  logs: string[]
}

interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'done' | 'error'
  progress: number
  message: string
  serial_numbers: string[]
  grafana_url?: string
  error?: string
  files?: FileInfo[]
}

function Upload() {
  const [isDragging, setIsDragging] = useState(false)
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [target, setTarget] = useState<ProcessingTarget>('grafana')
  const [isProcessing, setIsProcessing] = useState(false)
  const [showTargetSelection, setShowTargetSelection] = useState(false)
  const [activeJob, setActiveJob] = useState<{ jobId: string; itemId: string } | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const processingLockRef = useRef<boolean>(false) // Блокировка параллельной обработки

  // Генерация уникального ID для элемента очереди
  const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

  // Статистика очереди
  const stats = {
    total: queue.length,
    pending: queue.filter(q => q.status === 'pending').length,
    uploading: queue.filter(q => q.status === 'uploading').length,
    queued: queue.filter(q => q.status === 'queued').length,
    running: queue.filter(q => q.status === 'running').length,
    done: queue.filter(q => q.status === 'done').length,
    error: queue.filter(q => q.status === 'error').length,
  }

  // Обновление элемента очереди
  const updateQueueItem = useCallback((id: string, updates: Partial<QueueItem>) => {
    setQueue(prev => prev.map(item =>
      item.id === id ? { ...item, ...updates } : item
    ))
  }, [])

  // Добавление лога к элементу
  const addLog = useCallback((id: string, message: string) => {
    setQueue(prev => prev.map(item =>
      item.id === id ? { ...item, logs: [...item.logs, `[${new Date().toLocaleTimeString()}] ${message}`] } : item
    ))
  }, [])

  // Polling статуса job
  useEffect(() => {
    if (!activeJob) return

    const { jobId, itemId } = activeJob

    pollingRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/status/${jobId}`)
        if (!response.ok) return

        const status: JobStatus = await response.json()

        updateQueueItem(itemId, {
          processingProgress: status.progress,
          message: status.message,
          serialNumbers: status.serial_numbers,
          grafanaUrl: status.grafana_url,
          error: status.error,
        })

        // Добавляем сообщение в лог если оно изменилось
        if (status.message) {
          addLog(itemId, status.message)
        }

        // Для CSV targets получаем список файлов
        if ((target === 'csv' || target === 'perfmonkey') && (status.status === 'running' || status.status === 'done')) {
          try {
            const filesResponse = await fetch(`${API_URL}/api/files/${jobId}`)
            if (filesResponse.ok) {
              const filesData = await filesResponse.json()
              updateQueueItem(itemId, { files: filesData.files || [] })
            }
          } catch (err) {
            console.error('Error fetching files:', err)
          }
        }

        if (status.status === 'done') {
          updateQueueItem(itemId, { status: 'done' })
          addLog(itemId, '✅ Processing completed successfully')
          // Снимаем блокировку и очищаем активный job
          processingLockRef.current = false
          setActiveJob(null)
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
        }

        if (status.status === 'error') {
          updateQueueItem(itemId, {
            status: 'error',
            error: status.error || 'Processing failed'
          })
          addLog(itemId, `❌ Error: ${status.error || 'Processing failed'}`)
          // Снимаем блокировку и очищаем активный job
          processingLockRef.current = false
          setActiveJob(null)
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
        }
      } catch (err) {
        console.error('Error polling status:', err)
      }
    }, 2000)

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [activeJob, target, updateQueueItem, addLog])

  // Запуск обработки следующего файла из очереди (ПОСЛЕДОВАТЕЛЬНАЯ ОБРАБОТКА)
  // Файлы загружаются параллельно, но обрабатываются по одному
  useEffect(() => {
    if (!isProcessing) return
    if (activeJob) return // Есть активный job - ждём его завершения
    if (processingLockRef.current) return // Блокировка активна - предотвращаем race condition

    // Ищем файл готовый к обработке (уже загружен на сервер)
    const nextQueued = queue.find(q => q.status === 'queued')
    if (nextQueued && nextQueued.jobId) {
      // Устанавливаем блокировку и запускаем обработку
      processingLockRef.current = true
      startProcessingJob(nextQueued.id, nextQueued.jobId)
    } else {
      // Проверяем завершение всех операций
      const hasAnyActive = queue.some(q => 
        q.status === 'pending' || q.status === 'uploading' || q.status === 'queued' || q.status === 'running'
      )
      if (!hasAnyActive && queue.length > 0) {
        setIsProcessing(false)
      }
    }
  }, [queue, isProcessing, activeJob])

  // Запуск обработки job (polling)
  const startProcessingJob = (itemId: string, jobId: string) => {
    updateQueueItem(itemId, { status: 'running' })
    addLog(itemId, 'Starting processing...')
    setActiveJob({ jobId, itemId })
  }

  // Загрузка файла на сервер (только upload, без блокировки обработки)
  const uploadFile = async (itemId: string) => {
    const item = queue.find(q => q.id === itemId)
    if (!item) return

    updateQueueItem(itemId, { status: 'uploading', uploadProgress: 0 })
    addLog(itemId, `Starting upload: ${item.file.name}`)

    const formData = new FormData()
    formData.append('file', item.file)
    formData.append('target', target)

    try {
      const xhr = new XMLHttpRequest()

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100
          updateQueueItem(itemId, { uploadProgress: percentComplete })
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          const data = JSON.parse(xhr.responseText)
          // Файл загружен - ставим в очередь на обработку (queued)
          updateQueueItem(itemId, {
            status: 'queued',
            jobId: data.job_id,
            serialNumbers: data.serial_numbers,
            processingProgress: 0,
            message: 'Queued for processing...'
          })
          addLog(itemId, `✅ Upload complete. Job ID: ${data.job_id}`)
          if (data.serial_numbers?.length) {
            addLog(itemId, `Serial numbers: ${data.serial_numbers.join(', ')}`)
          }
          addLog(itemId, '⏳ Waiting in processing queue...')
        } else {
          let errorMsg = 'Upload failed'
          try {
            const errorData = JSON.parse(xhr.responseText)
            errorMsg = errorData.detail || errorMsg
          } catch { }
          updateQueueItem(itemId, {
            status: 'error',
            error: errorMsg
          })
          addLog(itemId, `❌ Upload failed: ${errorMsg}`)
        }
      })

      xhr.addEventListener('error', () => {
        updateQueueItem(itemId, {
          status: 'error',
          error: 'Network error during upload'
        })
        addLog(itemId, '❌ Network error during upload')
      })

      xhr.open('POST', `${API_URL}/api/upload`)
      xhr.send(formData)
    } catch (err) {
      updateQueueItem(itemId, {
        status: 'error',
        error: err instanceof Error ? err.message : 'Upload failed'
      })
      addLog(itemId, `❌ Error: ${err instanceof Error ? err.message : 'Upload failed'}`)
    }
  }

  // Drag & Drop handlers
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

    const droppedFiles = Array.from(e.dataTransfer.files)
    addFilesToQueue(droppedFiles)
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    addFilesToQueue(selectedFiles)
    // Reset input value to allow selecting same files again
    e.target.value = ''
  }, [])

  const addFilesToQueue = (files: File[]) => {
    const validFiles = files.filter(f => {
      const name = f.name.toLowerCase()
      return name.endsWith('.zip') || name.endsWith('.7z')
    })

    if (validFiles.length === 0) {
      alert('Please select .zip or .7z files only')
      return
    }

    const newItems: QueueItem[] = validFiles.map(file => ({
      id: generateId(),
      file,
      status: 'pending',
      uploadProgress: 0,
      processingProgress: 0,
      message: 'Waiting...',
      logs: []
    }))

    setQueue(prev => [...prev, ...newItems])
    setShowTargetSelection(true)
  }

  const removeFromQueue = (id: string) => {
    setQueue(prev => prev.filter(item => item.id !== id))
  }

  const clearQueue = () => {
    if (isProcessing) {
      if (!confirm('Processing is in progress. Are you sure you want to clear the queue?')) {
        return
      }
    }
    setQueue([])
    setIsProcessing(false)
    setActiveJob(null)
    processingLockRef.current = false
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    setShowTargetSelection(false)
  }

  const startProcessing = () => {
    if (queue.length === 0) return
    setIsProcessing(true)
    
    // Запускаем параллельную загрузку ВСЕХ pending файлов
    const pendingItems = queue.filter(q => q.status === 'pending')
    pendingItems.forEach(item => {
      uploadFile(item.id)
    })
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  const getStatusIcon = (status: QueueItemStatus) => {
    switch (status) {
      case 'pending':
        return <span className="status-icon pending">⏳</span>
      case 'uploading':
        return <Loader className="animate-spin status-icon uploading" size={18} />
      case 'queued':
        return <span className="status-icon queued">📋</span>
      case 'running':
        return <Loader className="animate-spin status-icon running" size={18} />
      case 'done':
        return <CheckCircle className="status-icon done" size={18} />
      case 'error':
        return <AlertCircle className="status-icon error" size={18} />
    }
  }

  const getStatusColor = (status: QueueItemStatus) => {
    switch (status) {
      case 'pending': return '#6b7280'
      case 'uploading': return '#3b82f6'
      case 'queued': return '#8b5cf6'  // purple - в очереди
      case 'running': return '#f59e0b'
      case 'done': return '#22c55e'
      case 'error': return '#ef4444'
    }
  }

  // Если очередь пуста - показываем dropzone
  if (queue.length === 0) {
    return (
      <div className="upload-container">
        <div className="upload-section">
          <div
            className={`dropzone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Files size={48} />
            <h2>Drag & Drop your archive files here</h2>
            <p>Supports multiple .zip and .7z files</p>
            <p className="hint">or</p>
            <label className="file-input-label">
              <input
                type="file"
                accept=".zip,.7z"
                multiple
                onChange={handleFileSelect}
                className="file-input"
              />
              <span>Browse Files</span>
            </label>
          </div>
        </div>
      </div>
    )
  }

  // Показываем очередь файлов
  return (
    <div className="upload-container batch-mode">
      {/* Header с статистикой */}
      <div className="batch-header">
        <div className="batch-stats">
          <span className="stat total">📦 Total: {stats.total}</span>
          {stats.pending > 0 && <span className="stat pending">⏳ Pending: {stats.pending}</span>}
          {stats.uploading > 0 && <span className="stat uploading">⬆️ Uploading: {stats.uploading}</span>}
          {stats.queued > 0 && <span className="stat queued">📋 Queued: {stats.queued}</span>}
          {stats.running > 0 && <span className="stat running">⚙️ Processing: {stats.running}</span>}
          {stats.done > 0 && <span className="stat done">✅ Done: {stats.done}</span>}
          {stats.error > 0 && <span className="stat error">❌ Errors: {stats.error}</span>}
        </div>

        <div className="batch-actions">
          {!isProcessing && queue.some(q => q.status === 'pending') && (
            <>
              <label className="file-input-label small">
                <input
                  type="file"
                  accept=".zip,.7z"
                  multiple
                  onChange={handleFileSelect}
                  className="file-input"
                />
                <span>+ Add More</span>
              </label>
            </>
          )}
          <button onClick={clearQueue} className="clear-button">
            <Trash2 size={16} />
            Clear All
          </button>
        </div>
      </div>

      {/* Выбор режима обработки */}
      {showTargetSelection && !isProcessing && (
        <div className="target-selection-bar">
          <span>Processing mode:</span>
          <div className="target-options">
            <button
              className={`target-option ${target === 'grafana' ? 'active' : ''}`}
              onClick={() => setTarget('grafana')}
            >
              <Database size={16} />
              Grafana
            </button>
            <button
              className={`target-option ${target === 'csv' ? 'active' : ''}`}
              onClick={() => setTarget('csv')}
            >
              <FileText size={16} />
              CSV Wide
            </button>
            <button
              className={`target-option ${target === 'perfmonkey' ? 'active' : ''}`}
              onClick={() => setTarget('perfmonkey')}
            >
              <FileText size={16} />
              CSV Perfmonkey
            </button>
          </div>

          <button onClick={startProcessing} className="start-button">
            <PlayCircle size={20} />
            Start Processing ({stats.pending} files)
          </button>
        </div>
      )}

      {/* Список файлов */}
      <div className="queue-list">
        {queue.map((item) => (
          <div key={item.id} className={`queue-item status-${item.status}`}>
            <div className="queue-item-header">
              <div className="queue-item-info">
                {getStatusIcon(item.status)}
                <span className="file-name">{item.file.name}</span>
                <span className="file-size">{formatBytes(item.file.size)}</span>
                {item.serialNumbers && item.serialNumbers.length > 0 && (
                  <span className="serial-badge">{item.serialNumbers.join(', ')}</span>
                )}
              </div>

              <div className="queue-item-actions">
                {item.status === 'done' && item.grafanaUrl && (
                  <a
                    href={item.grafanaUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="action-link grafana"
                  >
                    <ExternalLink size={14} />
                    Grafana
                  </a>
                )}
                {item.status === 'pending' && !isProcessing && (
                  <button
                    onClick={() => removeFromQueue(item.id)}
                    className="action-button remove"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {(item.status === 'uploading' || item.status === 'running') && (
              <div className="queue-item-progress">
                <div className="progress-bar-bg">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${item.status === 'uploading' ? item.uploadProgress : item.processingProgress}%`,
                      backgroundColor: getStatusColor(item.status)
                    }}
                  />
                </div>
                <span className="progress-text">
                  {item.status === 'uploading'
                    ? `Uploading: ${item.uploadProgress.toFixed(0)}%`
                    : `Processing: ${item.processingProgress}%`
                  }
                </span>
              </div>
            )}

            {/* Queued status indicator */}
            {item.status === 'queued' && (
              <div className="queue-item-queued">
                <span className="queued-text">📋 Waiting in processing queue...</span>
              </div>
            )}

            {/* Message */}
            {item.message && (item.status === 'running' || item.status === 'uploading') && (
              <div className="queue-item-message">{item.message}</div>
            )}

            {/* Error */}
            {item.status === 'error' && item.error && (
              <div className="queue-item-error">
                <AlertCircle size={14} />
                {item.error}
              </div>
            )}

            {/* CSV Files */}
            {item.status === 'done' && item.files && item.files.length > 0 && (
              <div className="queue-item-files">
                <strong>Generated files:</strong>
                <div className="files-list">
                  {item.files.map((file) => (
                    <a
                      key={file.name}
                      href={`${API_URL}${file.url}`}
                      download
                      className="file-download-link"
                    >
                      <Download size={12} />
                      {file.name} ({file.size_mb.toFixed(1)} MB)
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Logs (collapsible) */}
            {item.logs.length > 0 && (
              <details className="queue-item-logs">
                <summary>Logs ({item.logs.length})</summary>
                <div className="logs-content">
                  {item.logs.map((log, idx) => (
                    <div key={idx} className="log-line">{log}</div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}
      </div>

      {/* Final summary when all done */}
      {!isProcessing && stats.pending === 0 && stats.uploading === 0 && stats.queued === 0 && stats.running === 0 && queue.length > 0 && (
        <div className="batch-summary">
          <h3>🎉 Batch Processing Complete</h3>
          <div className="summary-stats">
            <span className="done">✅ Successful: {stats.done}</span>
            {stats.error > 0 && <span className="error">❌ Failed: {stats.error}</span>}
          </div>
          <button onClick={clearQueue} className="reset-button">
            Start New Batch
          </button>
        </div>
      )}
    </div>
  )
}

export default Upload
