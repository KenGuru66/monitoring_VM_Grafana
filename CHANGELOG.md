# Changelog

All notable changes to Huawei Storage Performance Monitoring project.

## [2.0.0] - 2025-10-09

### Added
- 🎯 **Multi-mode processing**: Grafana / CSV Wide / CSV Perfmonkey
- 🏠 **New Home page** with arrays and CSV jobs management
- ⚡ **Multi-threaded CSV compression** (16 threads, ~16x speedup)
- 📁 **CSV job management**: List, download, delete files via Web UI
- 🔄 **Auto-cleanup**: Jobs older than 24h automatically deleted
- 📥 **HTTP Range support** for resumable large file downloads
- 🔍 **Real-time file polling** for CSV jobs
- 📊 **Enhanced progress tracking** for all processing modes

### Changed
- 🎨 **Improved UI/UX**: Better visual layout for array cards
- 🔧 **Updated API**: New endpoints for CSV jobs and file management
- 📝 **Refactored documentation**: Clear, comprehensive guides
- 🐳 **Docker optimization**: Better volume management

### Fixed
- ✅ Fixed `target` parameter handling in upload form
- ✅ Fixed UI not showing CSV files for non-Grafana modes
- ✅ Fixed visual layout of array cards on home page
- ✅ Fixed frontend not updating after Docker rebuild

### Technical
- Added `Form()` dependency for correct multipart form data parsing
- Implemented `ThreadPoolExecutor` for parallel gzip compression
- Added `JOB_TTL_HOURS` configuration for auto-cleanup
- Enhanced job metadata with `target` and `files` fields
- Improved error handling and logging

## [1.0.0] - 2025-01-15

### Initial Release
- Basic Grafana integration
- VictoriaMetrics streaming pipeline
- Single CSV parser (wide format)
- Docker-based deployment
- Basic web interface

---

**Format:** Based on [Keep a Changelog](https://keepachangelog.com/)
**Versioning:** [Semantic Versioning](https://semver.org/)
