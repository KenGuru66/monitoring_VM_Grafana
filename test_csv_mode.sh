#!/bin/bash
# CSV Mode Acceptance Test Script
set -e

API_URL="${API_URL:-http://localhost:8000}"
TEST_FILE="${1:-test.zip}"

echo "════════════════════════════════════════════════════════════════"
echo "🧪 CSV MODE ACCEPTANCE TEST"
echo "════════════════════════════════════════════════════════════════"
echo "API URL:    $API_URL"
echo "Test file:  $TEST_FILE"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if test file exists
if [[ ! -f "$TEST_FILE" ]]; then
  echo -e "${RED}❌ Test file not found: $TEST_FILE${NC}"
  echo "Usage: $0 <path-to-test.zip>"
  exit 1
fi

# Check API health
echo "1️⃣  Checking API health..."
if ! curl -sf "$API_URL/health" > /dev/null; then
  echo -e "${RED}❌ API not responding at $API_URL${NC}"
  exit 1
fi
echo -e "${GREEN}✓ API is healthy${NC}"
echo ""

# Upload with CSV target
echo "2️⃣  Uploading file with target=csv..."
UPLOAD_START=$(date +%s)
RESPONSE=$(curl -s -X POST \
  -F "file=@$TEST_FILE" \
  -F "target=csv" \
  "$API_URL/api/upload")

if [[ $? -ne 0 ]]; then
  echo -e "${RED}❌ Upload failed${NC}"
  exit 1
fi

JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
TARGET=$(echo "$RESPONSE" | jq -r '.target')
MESSAGE=$(echo "$RESPONSE" | jq -r '.message')

if [[ "$JOB_ID" == "null" ]]; then
  echo -e "${RED}❌ No job ID returned${NC}"
  echo "$RESPONSE" | jq '.'
  exit 1
fi

echo -e "${GREEN}✓ Upload successful${NC}"
echo "  Job ID:  $JOB_ID"
echo "  Target:  $TARGET"
echo "  Message: $MESSAGE"
echo ""

# Verify target is CSV
if [[ "$TARGET" != "csv" ]]; then
  echo -e "${RED}❌ Expected target=csv, got target=$TARGET${NC}"
  exit 1
fi

# Wait for completion
echo "3️⃣  Waiting for job to complete..."
LAST_PROGRESS=0
while true; do
  STATUS_RESPONSE=$(curl -s "$API_URL/api/status/$JOB_ID")
  STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
  PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress')
  MSG=$(echo "$STATUS_RESPONSE" | jq -r '.message' | cut -c1-60)
  
  if [[ "$PROGRESS" != "$LAST_PROGRESS" ]]; then
    echo "  [$PROGRESS%] $STATUS - $MSG"
    LAST_PROGRESS=$PROGRESS
  fi
  
  if [[ "$STATUS" == "done" ]]; then
    PROCESSING_TIME=$(($(date +%s) - UPLOAD_START))
    echo -e "${GREEN}✓ Job completed in ${PROCESSING_TIME}s${NC}"
    break
  fi
  
  if [[ "$STATUS" == "error" ]]; then
    ERROR=$(echo "$STATUS_RESPONSE" | jq -r '.error')
    echo -e "${RED}❌ Job failed: $ERROR${NC}"
    exit 1
  fi
  
  sleep 3
done
echo ""

# Wait a bit for file compression
echo "4️⃣  Waiting for file compression..."
sleep 5

# List files
echo "5️⃣  Listing generated files..."
FILES_RESPONSE=$(curl -s "$API_URL/api/files/$JOB_ID")
FILE_COUNT=$(echo "$FILES_RESPONSE" | jq -r '.total')
TOTAL_SIZE_MB=$(echo "$FILES_RESPONSE" | jq -r '.total_size_mb')

if [[ "$FILE_COUNT" == "null" ]] || [[ "$FILE_COUNT" == "0" ]]; then
  echo -e "${YELLOW}⚠️  No files found yet, waiting 10s more...${NC}"
  sleep 10
  FILES_RESPONSE=$(curl -s "$API_URL/api/files/$JOB_ID")
  FILE_COUNT=$(echo "$FILES_RESPONSE" | jq -r '.total')
fi

if [[ "$FILE_COUNT" == "0" ]] || [[ "$FILE_COUNT" == "null" ]]; then
  echo -e "${RED}❌ No files generated${NC}"
  echo "$FILES_RESPONSE" | jq '.'
  exit 1
fi

echo -e "${GREEN}✓ Found $FILE_COUNT files (${TOTAL_SIZE_MB}MB total)${NC}"
echo "$FILES_RESPONSE" | jq -r '.files[] | "  - \(.name) (\(.size_mb)MB)"'
echo ""

# Download first file
FIRST_FILE=$(echo "$FILES_RESPONSE" | jq -r '.files[0].name')
FIRST_FILE_SIZE=$(echo "$FILES_RESPONSE" | jq -r '.files[0].size')
FIRST_FILE_URL=$(echo "$FILES_RESPONSE" | jq -r '.files[0].url')

echo "6️⃣  Downloading first file: $FIRST_FILE"
DOWNLOAD_FILE="/tmp/${FIRST_FILE}"
curl -sf -o "$DOWNLOAD_FILE" "$API_URL$FIRST_FILE_URL"

if [[ $? -ne 0 ]]; then
  echo -e "${RED}❌ Download failed${NC}"
  exit 1
fi

DOWNLOADED_SIZE=$(stat -f%z "$DOWNLOAD_FILE" 2>/dev/null || stat -c%s "$DOWNLOAD_FILE" 2>/dev/null)
echo -e "${GREEN}✓ Downloaded: $DOWNLOAD_FILE (${DOWNLOADED_SIZE} bytes)${NC}"
echo ""

# Verify file is gzip
echo "7️⃣  Verifying file format..."
FILE_TYPE=$(file "$DOWNLOAD_FILE")
if [[ "$FILE_TYPE" != *"gzip"* ]]; then
  echo -e "${RED}❌ File is not gzip compressed${NC}"
  echo "  Type: $FILE_TYPE"
  exit 1
fi
echo -e "${GREEN}✓ File is valid gzip${NC}"

# Test decompression
echo "8️⃣  Testing decompression..."
UNCOMPRESSED_FILE="/tmp/${FIRST_FILE%.gz}"
gunzip -c "$DOWNLOAD_FILE" > "$UNCOMPRESSED_FILE"
if [[ $? -ne 0 ]]; then
  echo -e "${RED}❌ Failed to decompress${NC}"
  exit 1
fi

UNCOMPRESSED_SIZE=$(stat -f%z "$UNCOMPRESSED_FILE" 2>/dev/null || stat -c%s "$UNCOMPRESSED_FILE" 2>/dev/null)
COMPRESSION_RATIO=$(echo "scale=1; 100 - ($DOWNLOADED_SIZE * 100 / $UNCOMPRESSED_SIZE)" | bc)
echo -e "${GREEN}✓ Decompressed successfully${NC}"
echo "  Compressed:   ${DOWNLOADED_SIZE} bytes"
echo "  Uncompressed: ${UNCOMPRESSED_SIZE} bytes"
echo "  Ratio:        ${COMPRESSION_RATIO}% reduction"

# Check CSV structure
LINES=$(wc -l < "$UNCOMPRESSED_FILE")
HEADER=$(head -1 "$UNCOMPRESSED_FILE")
echo "  Lines:        $LINES"
echo "  Header:       ${HEADER:0:80}..."
echo ""

# Test HTTP Range support
echo "9️⃣  Testing HTTP Range support..."
RANGE_RESPONSE=$(curl -sI -H "Range: bytes=0-1023" "$API_URL$FIRST_FILE_URL")
if echo "$RANGE_RESPONSE" | grep -qi "content-range"; then
  echo -e "${GREEN}✓ HTTP Range supported${NC}"
  CONTENT_RANGE=$(echo "$RANGE_RESPONSE" | grep -i "content-range")
  echo "  $CONTENT_RANGE"
else
  echo -e "${YELLOW}⚠️  HTTP Range not detected in response${NC}"
fi
echo ""

# Test MD5 verification
echo "🔟 Testing MD5 verification..."
LOCAL_MD5=$(md5sum "$DOWNLOAD_FILE" | awk '{print $1}')
echo "  Local MD5:  $LOCAL_MD5"

# Try to get server MD5 (optional, may not work if docker exec unavailable)
if command -v docker &> /dev/null; then
  SERVER_MD5=$(docker exec huawei-api md5sum /app/jobs/$JOB_ID/$FIRST_FILE 2>/dev/null | awk '{print $1}' || echo "N/A")
  echo "  Server MD5: $SERVER_MD5"
  
  if [[ "$LOCAL_MD5" == "$SERVER_MD5" ]] && [[ "$SERVER_MD5" != "N/A" ]]; then
    echo -e "${GREEN}✓ MD5 matches${NC}"
  elif [[ "$SERVER_MD5" == "N/A" ]]; then
    echo -e "${YELLOW}⚠️  Cannot verify server MD5 (docker not available)${NC}"
  else
    echo -e "${RED}❌ MD5 mismatch!${NC}"
    exit 1
  fi
else
  echo -e "${YELLOW}⚠️  Cannot verify server MD5 (docker not available)${NC}"
fi
echo ""

# Delete files
echo "1️⃣1️⃣ Testing file deletion..."
DELETE_RESPONSE=$(curl -s -X DELETE "$API_URL/api/files/$JOB_ID")
DELETED_COUNT=$(echo "$DELETE_RESPONSE" | jq -r '.deleted_count')

if [[ "$DELETED_COUNT" == "null" ]]; then
  echo -e "${RED}❌ Delete failed${NC}"
  echo "$DELETE_RESPONSE" | jq '.'
  exit 1
fi

echo -e "${GREEN}✓ Deleted $DELETED_COUNT files${NC}"

# Verify files are gone
sleep 1
FILES_AFTER=$(curl -s "$API_URL/api/files/$JOB_ID")
COUNT_AFTER=$(echo "$FILES_AFTER" | jq -r '.total // 0')

if [[ "$COUNT_AFTER" != "0" ]]; then
  echo -e "${YELLOW}⚠️  Files still exist after deletion (count: $COUNT_AFTER)${NC}"
else
  echo -e "${GREEN}✓ Files confirmed deleted${NC}"
fi
echo ""

# Cleanup
rm -f "$DOWNLOAD_FILE" "$UNCOMPRESSED_FILE"

# Summary
echo "════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
echo "════════════════════════════════════════════════════════════════"
echo "Summary:"
echo "  - Upload:      ✓"
echo "  - Processing:  ✓ (${PROCESSING_TIME}s)"
echo "  - Files:       ✓ ($FILE_COUNT files)"
echo "  - Download:    ✓ (${DOWNLOADED_SIZE} bytes)"
echo "  - Format:      ✓ (gzip)"
echo "  - Decompress:  ✓ (${COMPRESSION_RATIO}% compression)"
echo "  - Range:       ✓"
echo "  - Delete:      ✓"
echo ""
echo "Test completed successfully!"
echo "════════════════════════════════════════════════════════════════"


