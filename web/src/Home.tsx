import { useState, useEffect } from 'react'
import { Trash2, AlertTriangle, RefreshCw, Server, ExternalLink } from 'lucide-react'
import './Home.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3000'

function Home() {
    const [arrays, setArrays] = useState<string[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

    const loadArrays = async () => {
        setLoading(true)
        setError(null)

        try {
            const response = await fetch(`${API_URL}/api/arrays`)
            if (!response.ok) throw new Error('Failed to fetch arrays')

            const data = await response.json()
            setArrays(data.arrays || [])
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load arrays')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadArrays()
    }, [])

    const showToast = (message: string, type: 'success' | 'error') => {
        setToast({ message, type })
        setTimeout(() => setToast(null), 5000)
    }

    const handleDeleteArray = async (sn: string) => {
        try {
            const response = await fetch(`${API_URL}/api/arrays/${sn}`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                throw new Error(error.detail || 'Delete failed')
            }

            showToast(`Array ${sn} deleted successfully`, 'success')
            await loadArrays()
        } catch (err) {
            showToast(err instanceof Error ? err.message : 'Delete failed', 'error')
        } finally {
            setDeleteConfirm(null)
        }
    }

    const handleDeleteAll = async () => {
        if (!window.confirm('⚠️ Are you sure you want to delete ALL arrays?\n\nThis will remove all performance data from VictoriaMetrics.\n\nThis action CANNOT be undone!')) {
            setDeleteConfirm(null)
            return
        }

        try {
            const response = await fetch(`${API_URL}/api/arrays`, {
                method: 'DELETE',
            })

            if (!response.ok) {
                const error = await response.json()
                throw new Error(error.detail || 'Delete failed')
            }

            showToast('All arrays deleted successfully', 'success')
            await loadArrays()
        } catch (err) {
            showToast(err instanceof Error ? err.message : 'Delete failed', 'error')
        } finally {
            setDeleteConfirm(null)
        }
    }

    return (
        <div className="home-container">
            <header className="home-header">
                <div className="header-content">
                    <Server size={32} />
                    <h1>Imported Arrays</h1>
                </div>
                <p className="subtitle">Manage performance data from Huawei storage arrays</p>
            </header>

            {toast && (
                <div className={`toast toast-${toast.type}`}>
                    {toast.message}
                </div>
            )}

            <div className="home-content">
                <div className="actions-bar">
                    <button onClick={loadArrays} className="btn-refresh" disabled={loading}>
                        <RefreshCw size={18} className={loading ? 'spinning' : ''} />
                        Refresh
                    </button>

                    {arrays.length > 0 && (
                        <button onClick={() => setDeleteConfirm('all')} className="btn-delete-all">
                            <Trash2 size={18} />
                            Delete All Arrays
                        </button>
                    )}
                </div>

                {error && (
                    <div className="error-box">
                        <AlertTriangle size={20} />
                        <span>{error}</span>
                    </div>
                )}

                {loading ? (
                    <div className="loading-state">
                        <RefreshCw size={48} className="spinning" />
                        <p>Loading arrays...</p>
                    </div>
                ) : arrays.length === 0 ? (
                    <div className="empty-state">
                        <Server size={64} opacity={0.3} />
                        <h2>No Arrays Found</h2>
                        <p>Upload performance logs to see arrays here</p>
                        <a href="/upload" className="btn-upload">
                            Go to Upload
                        </a>
                    </div>
                ) : (
                    <div className="arrays-grid">
                        {arrays.map((sn) => (
                            <div key={sn} className="array-card">
                                <div className="array-header">
                                    <Server size={24} />
                                    <h3>{sn}</h3>
                                </div>

                                <div className="array-actions">
                                    <a
                                        href={`${GRAFANA_URL}/d/huawei-oceanstor-real/huawei-oceanstor-real-data?var-SN=${sn}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="btn-grafana"
                                    >
                                        <ExternalLink size={16} />
                                        View in Grafana
                                    </a>

                                    <button
                                        onClick={() => setDeleteConfirm(sn)}
                                        className="btn-delete"
                                    >
                                        <Trash2 size={16} />
                                        Delete
                                    </button>
                                </div>

                                {deleteConfirm === sn && (
                                    <div className="delete-confirm">
                                        <p>Delete array {sn}?</p>
                                        <div className="confirm-actions">
                                            <button onClick={() => handleDeleteArray(sn)} className="btn-confirm-yes">
                                                Yes, Delete
                                            </button>
                                            <button onClick={() => setDeleteConfirm(null)} className="btn-confirm-no">
                                                Cancel
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}

                {deleteConfirm === 'all' && (
                    <div className="modal-overlay">
                        <div className="modal-content">
                            <AlertTriangle size={48} color="#ef4444" />
                            <h2>Delete All Arrays?</h2>
                            <p>This will permanently delete ALL performance data from VictoriaMetrics.</p>
                            <p><strong>Found {arrays.length} array(s)</strong></p>
                            <p className="warning-text">This action CANNOT be undone!</p>

                            <div className="modal-actions">
                                <button onClick={handleDeleteAll} className="btn-modal-delete">
                                    <Trash2 size={18} />
                                    Yes, Delete All
                                </button>
                                <button onClick={() => setDeleteConfirm(null)} className="btn-modal-cancel">
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default Home

