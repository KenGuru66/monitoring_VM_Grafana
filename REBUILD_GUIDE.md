# Rebuild & Test Guide - Multi-Mode Processing

## 🔄 Rebuild Containers

Код обновлён, но контейнеры работают на старой версии. Нужно пересобрать:

### 1. Stop Services

```bash
cd /data/projects/monitoring_VM_Grafana
docker-compose down
```

### 2. Rebuild Containers

```bash
# Rebuild API (includes new routes and HTTP Range support)
docker-compose build --no-cache api

# Rebuild Web (includes CSV files table UI)
docker-compose build --no-cache web

# Or rebuild all
docker-compose build --no-cache
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Verify Services

```bash
# Check all services are running
docker-compose ps

# Check API logs
docker-compose logs -f api

# Check web logs
docker-compose logs -f web
```

## ✅ Test CSV Mode (Acceptance Tests)

### Test 1: Upload with CSV Target

```bash
# Upload test archive with CSV mode
curl -X POST \
  -F "file=@test.zip" \
  -F "target=csv" \
  http://localhost:8000/api/upload

# Response should include:
{
  "job_id": "550e8400-...",
  "target": "csv",
  "message": "Upload successful, processing started (CSV wide format)"
}
```

### Test 2: Check Job Status

```bash
JOB_ID="<job_id_from_above>"

# Poll status
curl http://localhost:8000/api/status/$JOB_ID

# Should show:
{
  "status": "running",
  "progress": 50,
  "target": "csv",
  ...
}
```

### Test 3: List Generated Files

```bash
# Wait for job to complete (status=done)
# Then list files
curl http://localhost:8000/api/files/$JOB_ID

# Should return:
{
  "job_id": "550e8400-...",
  "files": [
    {
      "name": "cpu_output.csv.gz",
      "size": 1048576,
      "size_mb": 1.0,
      "modified": "2025-10-09T14:30:00",
      "url": "/api/file/550e8400-.../cpu_output.csv.gz"
    },
    ...
  ],
  "total": 5,
  "total_size_mb": 50.0
}
```

### Test 4: Download Files

```bash
# Download single file
curl -O http://localhost:8000/api/file/$JOB_ID/cpu_output.csv.gz

# Verify file
ls -lh cpu_output.csv.gz
gunzip cpu_output.csv.gz
head cpu_output.csv
```

### Test 5: Test HTTP Range (Resume)

```bash
# Download first 1MB only
curl -H "Range: bytes=0-1048575" \
  -o cpu_partial.csv.gz \
  http://localhost:8000/api/file/$JOB_ID/cpu_output.csv.gz

# Check partial download
ls -lh cpu_partial.csv.gz
# Should be exactly 1MB

# Resume from 1MB onwards
curl -H "Range: bytes=1048576-" \
  -o cpu_rest.csv.gz \
  http://localhost:8000/api/file/$JOB_ID/cpu_output.csv.gz

# Combine and verify
cat cpu_partial.csv.gz cpu_rest.csv.gz > cpu_combined.csv.gz
md5sum cpu_combined.csv.gz
# Should match original download
```

### Test 6: MD5 Verification

```bash
# Calculate MD5 on server
docker exec huawei-api md5sum /app/jobs/$JOB_ID/cpu_output.csv.gz

# Calculate MD5 of downloaded file
md5sum cpu_output.csv.gz

# Should match
```

### Test 7: Delete Files via API

```bash
# Delete all files for job
curl -X DELETE http://localhost:8000/api/files/$JOB_ID

# Should return:
{
  "message": "Deleted 5 files",
  "job_id": "550e8400-...",
  "deleted_count": 5
}

# Verify files are gone
curl http://localhost:8000/api/files/$JOB_ID
# Should return 404 or empty list
```

## 🖥️ UI Tests (Manual)

### Test 1: Upload with CSV Mode

1. Open browser: `http://localhost:3001`
2. Upload ZIP file
3. **Click "Parse → CSV (Wide)"** button
4. Wait for upload to complete

**Expected:**
- Upload progress bar shows 100%
- Processing starts immediately

### Test 2: No Grafana Button for CSV

**Expected:**
- ❌ NO "Open in Grafana" button visible
- ✅ Message: "Files are being compressed, please wait..."
- ✅ Spinning loader icon

### Test 3: Files Table Appears

Wait ≤30 seconds after job status = "done"

**Expected:**
- ✅ Table appears with columns: Filename | Size | Modified | Action
- ✅ Each file has green "Download" button
- ✅ Total file count shown: "📁 Generated Files (5)"

### Test 4: Download Files via UI

Click "Download" button on any file

**Expected:**
- ✅ Browser downloads file immediately
- ✅ Filename is correct (e.g., `cpu_output.csv.gz`)
- ✅ File opens in archive manager / unzips correctly

### Test 5: Delete Files via UI

Click "Delete All Files" button

**Expected:**
- ✅ Confirmation or immediate deletion
- ✅ Files disappear from table
- ✅ Message: "No files generated yet..."

### Test 6: Grafana Mode Still Works

1. Upload new ZIP file
2. **Click "Parse → Grafana"** button
3. Wait for completion

**Expected:**
- ✅ "Open in Grafana" button appears (orange)
- ✅ NO files table
- ✅ Clicking button opens Grafana dashboard

## 📊 Performance Benchmarks

### Expected Performance (CSV mode)

| Input Size | Processing Time | Output Size (gzipped) | Files Generated |
|------------|----------------|----------------------|-----------------|
| 100MB ZIP | 2-3 min | ~30MB | 5-8 files |
| 500MB ZIP | 8-12 min | ~150MB | 5-8 files |
| 2GB ZIP | 30-40 min | ~600MB | 5-8 files |

### Compression Ratio

- Typical: 60-70% size reduction
- Example: 500MB CSV → 150MB .csv.gz

### Download Speed

- Local network: ~100 MB/s
- HTTP Range: Supports resume from any byte offset

## 🐛 Troubleshooting

### Issue: UI Still Shows Grafana Button for CSV

**Cause:** Web container not rebuilt

**Solution:**
```bash
docker-compose build --no-cache web
docker-compose restart web
# Clear browser cache: Ctrl+Shift+R
```

### Issue: Files Table Empty After 5 Minutes

**Cause:** gzip compression failed or job stuck

**Solution:**
```bash
# Check job status
curl http://localhost:8000/api/status/$JOB_ID

# Check files on disk
docker exec huawei-api ls -lh /app/jobs/$JOB_ID/

# Check API logs for errors
docker-compose logs api | grep ERROR
```

### Issue: Download Fails with 404

**Cause:** Job directory deleted or wrong job_id

**Solution:**
```bash
# Verify job exists
curl http://localhost:8000/api/jobs

# Check if files exist
docker exec huawei-api ls -lh /app/jobs/$JOB_ID/

# Regenerate by re-uploading
```

### Issue: Large File Download Interrupted

**Cause:** Network timeout or browser issue

**Solution:**
```bash
# Use curl with resume support
curl -C - -O http://localhost:8000/api/file/$JOB_ID/large_file.csv.gz

# Or use wget
wget -c http://localhost:8000/api/file/$JOB_ID/large_file.csv.gz
```

### Issue: Cannot Delete Files via UI

**Cause:** Permission error or API unreachable

**Solution:**
```bash
# Delete manually via Docker
docker exec huawei-api rm -rf /app/jobs/$JOB_ID/

# Or delete via API directly
curl -X DELETE http://localhost:8000/api/files/$JOB_ID
```

## 🔍 Verification Checklist

Before considering deployment complete, verify:

- [ ] API responds to `/health` (200 OK)
- [ ] Web UI loads without errors (F12 console clear)
- [ ] Upload with `target=csv` works
- [ ] No Grafana button for CSV mode
- [ ] Files table appears within 30s of completion
- [ ] Download button works for each file
- [ ] Downloaded file unzips correctly
- [ ] MD5 matches server file
- [ ] HTTP Range header supported (check with `curl -I`)
- [ ] Delete files button works
- [ ] Grafana mode still works (upload with `target=grafana`)
- [ ] Perfmonkey mode works (upload with `target=perfmonkey`)

## 📝 Quick Test Script

Save as `test_csv_mode.sh`:

```bash
#!/bin/bash
set -e

echo "🧪 Testing CSV Mode..."

# 1. Upload
echo "1️⃣ Uploading test archive..."
RESPONSE=$(curl -s -X POST \
  -F "file=@test.zip" \
  -F "target=csv" \
  http://localhost:8000/api/upload)

JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "   Job ID: $JOB_ID"

# 2. Wait for completion
echo "2️⃣ Waiting for job to complete..."
while true; do
  STATUS=$(curl -s http://localhost:8000/api/status/$JOB_ID | jq -r '.status')
  PROGRESS=$(curl -s http://localhost:8000/api/status/$JOB_ID | jq -r '.progress')
  echo "   Status: $STATUS ($PROGRESS%)"
  
  [[ "$STATUS" == "done" ]] && break
  [[ "$STATUS" == "error" ]] && exit 1
  
  sleep 5
done

# 3. List files
echo "3️⃣ Listing generated files..."
FILES=$(curl -s http://localhost:8000/api/files/$JOB_ID | jq -r '.files[] | .name')
echo "$FILES"

# 4. Download first file
FIRST_FILE=$(echo "$FILES" | head -1)
echo "4️⃣ Downloading $FIRST_FILE..."
curl -sO http://localhost:8000/api/file/$JOB_ID/$FIRST_FILE

# 5. Verify download
echo "5️⃣ Verifying download..."
ls -lh $FIRST_FILE
file $FIRST_FILE

# 6. Test Range support
echo "6️⃣ Testing HTTP Range support..."
RANGE_RESPONSE=$(curl -sI -H "Range: bytes=0-1024" \
  http://localhost:8000/api/file/$JOB_ID/$FIRST_FILE | grep -i "content-range")
echo "   $RANGE_RESPONSE"

# 7. Delete files
echo "7️⃣ Deleting files..."
curl -s -X DELETE http://localhost:8000/api/files/$JOB_ID | jq '.'

echo "✅ All tests passed!"
```

Run:
```bash
chmod +x test_csv_mode.sh
./test_csv_mode.sh
```

## 🎯 Success Criteria

✅ **ALL of these must pass:**

1. Upload with `target=csv` creates job
2. Job processes to 100% without errors
3. UI shows **NO** Grafana button for CSV mode
4. UI shows files table within 30 seconds
5. Each file can be downloaded via browser
6. Downloaded files are valid gzip archives
7. Files can be uncompressed and read
8. HTTP Range headers work (`curl -I` shows `Accept-Ranges: bytes`)
9. Delete button removes files from server
10. Grafana mode (`target=grafana`) still works independently

---

**Last Updated:** October 9, 2025  
**Version:** 2.0.1


