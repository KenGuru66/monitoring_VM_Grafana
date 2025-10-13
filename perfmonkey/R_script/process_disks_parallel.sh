#!/bin/bash
# process_disks_parallel.sh - Efficiently process disk data in parallel

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_file> [num_jobs]"
    exit 1
fi

INPUT_FILE="$1"
NUM_JOBS="${2:-20}"  # Default 20 parallel jobs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(dirname "$INPUT_FILE")"
BASE_NAME=$(basename "$INPUT_FILE" | sed 's/\.csv.*$//')

echo "═══════════════════════════════════════════════════════════════"
echo "  DISK PERFORMANCE → PERFMONKEY (EFFICIENT PARALLEL)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Input file: $INPUT_FILE"
echo "Parallel jobs: $NUM_JOBS"
echo "Working directory: $WORK_DIR"
echo ""

# Create temp directory for split files
TEMP_DIR="${WORK_DIR}/disk_split_$$"
mkdir -p "$TEMP_DIR"

echo "Step 1: Splitting file by disk instances..."
START_TIME=$(date +%s)

# Get header
head -1 "$INPUT_FILE" > "${TEMP_DIR}/header.txt"

# Split by instance (disk)
awk -F';' 'NR>1 {
    instance = $3
    gsub(/\./, "_", instance)
    gsub(/\//, "_", instance)
    print > "'${TEMP_DIR}'/disk_" instance ".csv"
}' "$INPUT_FILE"

# Add headers to each file
for f in ${TEMP_DIR}/disk_*.csv; do
    if [ -f "$f" ]; then
        temp="${f}.tmp"
        cat "${TEMP_DIR}/header.txt" "$f" > "$temp"
        mv "$temp" "$f"
    fi
done

SPLIT_END=$(date +%s)
SPLIT_TIME=$((SPLIT_END - START_TIME))
NUM_FILES=$(ls -1 ${TEMP_DIR}/disk_*.csv 2>/dev/null | wc -l)

echo "  ✓ Split into $NUM_FILES files in ${SPLIT_TIME}s"
echo ""

# Start monitoring in background
monitor_resources() {
    while true; do
        CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
        MEM=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
        PROCESSES=$(pgrep -f "parse_single_disk.R" | wc -l)
        echo -ne "\r⚡ CPU: ${CPU}% | 💾 Memory: ${MEM} | 🔄 Active: ${PROCESSES}/${NUM_JOBS}     "
        sleep 2
    done
}

echo "Step 2: Processing disks in parallel (max $NUM_JOBS jobs)..."
echo ""

# Start resource monitor
monitor_resources &
MONITOR_PID=$!

# Process files in parallel using xargs
PROCESS_START=$(date +%s)

ls -1 ${TEMP_DIR}/disk_*.csv | \
    xargs -P ${NUM_JOBS} -I {} sh -c "Rscript ${SCRIPT_DIR}/parse_single_disk.R {} 2>&1 | sed 's/^/  ✓ /'" || true

# Kill monitor
kill $MONITOR_PID 2>/dev/null
echo ""

PROCESS_END=$(date +%s)
PROCESS_TIME=$((PROCESS_END - PROCESS_START))

echo ""
echo "Step 3: Moving output files..."

# Move output files and cleanup
mv ${TEMP_DIR}/*_output.csv "${WORK_DIR}/" 2>/dev/null || true
rm -rf "$TEMP_DIR"

TOTAL_TIME=$((PROCESS_END - START_TIME))

echo "  ✓ Output files moved to: $WORK_DIR"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ COMPLETED SUCCESSFULLY!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Files processed: $NUM_FILES"
echo "Split time: ${SPLIT_TIME}s"
echo "Processing time: ${PROCESS_TIME}s"
echo "Total time: ${TOTAL_TIME}s"
echo "Average per file: $((PROCESS_TIME / NUM_FILES))s"
echo ""
echo "Output files pattern: ${WORK_DIR}/disk_*_output.csv"
echo ""
echo "Files are ready for PerfMonkey import! 🚀"
echo ""

