import { useState } from 'react'
import { Upload as UploadIcon } from 'lucide-react'
import Home from './Home'
import Upload from './Upload'
import './App.css'

function App() {
    const [currentPage, setCurrentPage] = useState<'home' | 'upload'>('home')

    return (
        <div className="app">
            <nav className="app-nav">
                <div className="nav-content">
                    <button
                        className={`nav-btn ${currentPage === 'home' ? 'active' : ''}`}
                        onClick={() => setCurrentPage('home')}
                    >
                        Home
                    </button>
                    <button
                        className={`nav-btn ${currentPage === 'upload' ? 'active' : ''}`}
                        onClick={() => setCurrentPage('upload')}
                    >
                        <UploadIcon size={18} />
                        Upload
                    </button>
                </div>
            </nav>

            {currentPage === 'home' ? <Home /> : <Upload />}
        </div>
    )
}

export default App
