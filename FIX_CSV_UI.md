# CSV Mode UI Fix - Quick Guide

## 🎯 Problem

When uploading with `target=csv` or `target=perfmonkey`, the UI incorrectly shows:
- ❌ "Open in Grafana" button (should only appear for `target=grafana`)
- ❌ No files table or download links

## ✅ Solution

Code has been updated to fix this issue. You just need to rebuild the containers.

## 🚀 Quick Fix (2 minutes)

```bash
cd /data/projects/monitoring_VM_Grafana

# Rebuild containers with new code
./rebuild.sh

# Clear browser cache
# Chrome/Firefox: Ctrl+Shift+R (or Cmd+Shift+R on Mac)

# Test it
./test_csv_mode.sh test.zip
```

## 📋 What Changed

### Backend (API)
- ✅ Added HTTP Range support for resumable downloads
- ✅ Added proper Content-Disposition headers
- ✅ Better media type detection

### Frontend (Web UI)
- ✅ Conditional button display based on target type
- ✅ Loading indicator while files compress
- ✅ Files table appears automatically for CSV modes

## 🧪 Manual Test

1. **Open browser:** `http://localhost:3001`
2. **Upload ZIP file**
3. **Click:** "Parse → CSV (Wide)" button
4. **Wait for completion**

**Expected Result:**
```
✅ NO "Open in Grafana" button
✅ "Files are being compressed..." message with spinner
✅ Files table appears within 30 seconds
✅ Each file has a green "Download" button
✅ Downloaded files are valid .csv.gz archives
```

## 📊 Automated Test

```bash
# Create test archive (if you don't have one)
# Use any existing Huawei performance ZIP file

# Run acceptance test
./test_csv_mode.sh /path/to/test.zip
```

**Expected Output:**
```
════════════════════════════════════════════════════════════════
🧪 CSV MODE ACCEPTANCE TEST
════════════════════════════════════════════════════════════════
1️⃣  Checking API health...
✓ API is healthy

2️⃣  Uploading file with target=csv...
✓ Upload successful
  Job ID:  550e8400-...
  Target:  csv

3️⃣  Waiting for job to complete...
  [100%] done - CSV files ready for download!
✓ Job completed in 125s

4️⃣  Waiting for file compression...

5️⃣  Listing generated files...
✓ Found 5 files (50.5MB total)
  - cpu_output.csv.gz (12.3MB)
  - disk_output.csv.gz (8.1MB)
  ...

6️⃣  Downloading first file: cpu_output.csv.gz
✓ Downloaded: /tmp/cpu_output.csv.gz (12891234 bytes)

7️⃣  Verifying file format...
✓ File is valid gzip

8️⃣  Testing decompression...
✓ Decompressed successfully
  Compressed:   12891234 bytes
  Uncompressed: 35678901 bytes
  Ratio:        63.8% reduction

9️⃣  Testing HTTP Range support...
✓ HTTP Range supported

🔟 Testing MD5 verification...
✓ MD5 matches

1️⃣1️⃣ Testing file deletion...
✓ Deleted 5 files
✓ Files confirmed deleted

════════════════════════════════════════════════════════════════
✅ ALL TESTS PASSED
════════════════════════════════════════════════════════════════
```

## 🔍 Troubleshooting

### Issue: Still shows Grafana button

**Cause:** Browser cache

**Fix:**
```bash
# Hard refresh browser
# Chrome/Firefox: Ctrl+Shift+R
# Safari: Cmd+Option+R

# Or rebuild web container again
docker-compose build --no-cache web
docker-compose restart web
```

### Issue: Files table empty after 5 minutes

**Check job status:**
```bash
JOB_ID="your-job-id"
curl http://localhost:8000/api/status/$JOB_ID
```

**Check files on disk:**
```bash
docker exec huawei-api ls -lh /app/jobs/$JOB_ID/
```

**Check logs:**
```bash
docker-compose logs api | grep ERROR
docker-compose logs api | tail -100
```

### Issue: Download fails

**Test directly with curl:**
```bash
JOB_ID="your-job-id"
FILE="cpu_output.csv.gz"
curl -O http://localhost:8000/api/file/$JOB_ID/$FILE
```

**Check file exists:**
```bash
docker exec huawei-api ls -lh /app/jobs/$JOB_ID/$FILE
```

## 📸 Screenshots

### ✅ CORRECT (After Fix)

**Grafana Mode:**
```
[Upload Complete]
┌─────────────────────────┐
│ 🟢 Processing Complete! │
├─────────────────────────┤
│                         │
│  [🟠 Open in Grafana]   │  ← Only for target=grafana
│                         │
│  [Upload Another File]  │
└─────────────────────────┘
```

**CSV Mode:**
```
[Upload Complete]
┌─────────────────────────────────────────┐
│ 🟢 Processing Complete!                 │
├─────────────────────────────────────────┤
│ 📁 Generated Files (5)                  │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Filename      │ Size  │ Download    │ │
│ ├─────────────────────────────────────┤ │
│ │ cpu_output... │ 12 MB │ [⬇ Download]│ │
│ │ disk_output...│  8 MB │ [⬇ Download]│ │
│ └─────────────────────────────────────┘ │
│                                         │
│  [🗑️ Delete All Files]                  │
│  [Upload Another File]                  │
└─────────────────────────────────────────┘
```

### ❌ INCORRECT (Before Fix)

**CSV Mode (Wrong):**
```
[Upload Complete]
┌─────────────────────────┐
│ 🟢 Processing Complete! │
├─────────────────────────┤
│                         │
│  [🟠 Open in Grafana]   │  ← WRONG! Should not appear
│                         │
│  [Upload Another File]  │
└─────────────────────────┘
```

## 🎯 Verification Checklist

After rebuild, verify:

- [ ] `docker-compose ps` shows all services running
- [ ] API responds: `curl http://localhost:8000/health`
- [ ] Web UI loads: `http://localhost:3001`
- [ ] Upload with `target=csv` works
- [ ] NO Grafana button for CSV mode
- [ ] Files table appears within 30s
- [ ] Download button works
- [ ] Files are valid gzip archives
- [ ] Upload with `target=grafana` still shows Grafana button

## 📚 Related Documentation

- `REBUILD_GUIDE.md` - Detailed rebuild & test guide
- `CHANGELOG.md` - Version history and changes
- `FEATURE_MULTI_MODE.md` - Complete feature documentation
- `DEPLOYMENT.md` - Production deployment guide

## ⏱️ Timeline

| Step | Time | Action |
|------|------|--------|
| 1 | 30s | Stop services |
| 2 | 2min | Rebuild API container |
| 3 | 1min | Rebuild Web container |
| 4 | 30s | Start services |
| 5 | 10s | Verify health |
| **Total** | **~5min** | **Complete fix** |

## 🎉 Success Criteria

When everything works correctly:

1. ✅ Upload with `target=csv` → Files table appears
2. ✅ Upload with `target=csv` → NO Grafana button
3. ✅ Files download successfully via browser
4. ✅ Files are valid .csv.gz archives
5. ✅ Upload with `target=grafana` → Grafana button appears
6. ✅ HTTP Range supported (resume downloads)
7. ✅ Delete button removes files

---

**Quick Commands:**
```bash
# Fix everything
./rebuild.sh

# Test everything
./test_csv_mode.sh test.zip

# View logs
docker-compose logs -f api
```

**Need help?** Check `REBUILD_GUIDE.md` for detailed troubleshooting.

---

**Version:** 2.0.1  
**Date:** October 9, 2025


