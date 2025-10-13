#!/bin/bash
# run_with_monitor.sh - Run disk parser with live monitoring

INPUT_FILE="$1"
NUM_WORKERS="${2:-30}"

if [ -z "$INPUT_FILE" ]; then
    echo "Usage: $0 <input_file> [num_workers]"
    echo "Example: $0 file.csv 30"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="disk_processing_parallel.log"

# Start processing in background
echo "Starting parallel disk processing..."
echo "Workers: $NUM_WORKERS"
echo "Log file: $LOG_FILE"
echo ""

python3 "$SCRIPT_DIR/parse_disk_parallel.py" "$INPUT_FILE" "$NUM_WORKERS" > "$LOG_FILE" 2>&1 &
PROC_PID=$!

echo "Process PID: $PROC_PID"
echo ""
echo "Monitoring (press Ctrl+C to stop monitoring, process will continue)..."
echo "═══════════════════════════════════════════════════════════════"

# Monitor until process completes
while kill -0 $PROC_PID 2>/dev/null; do
    CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    MEM=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
    PYTHON_PROCS=$(pgrep -P $PROC_PID | wc -l)
    
    # Get last line from log
    if [ -f "$LOG_FILE" ]; then
        LAST_LINE=$(tail -1 "$LOG_FILE" 2>/dev/null | head -c 60)
    else
        LAST_LINE="Starting..."
    fi
    
    echo -ne "\r⚡ CPU: ${CPU}% | 💾 Memory: ${MEM} | 🔄 Workers: ${PYTHON_PROCS} | ${LAST_LINE}     "
    sleep 1
done

echo ""
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Process completed! Final output:"
echo "═══════════════════════════════════════════════════════════════"
echo ""
tail -30 "$LOG_FILE"

