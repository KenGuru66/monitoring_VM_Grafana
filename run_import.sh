#!/bin/bash
# Wrapper script for csv2vm.py with logging

CSV_FILE="$1"
BATCH_SIZE="${2:-100000}"
LOG_FILE="import_$(date +%Y%m%d_%H%M%S).log"

echo "===================================================================" | tee -a "$LOG_FILE"
echo "Starting CSV import at $(date)" | tee -a "$LOG_FILE"
echo "CSV file: $CSV_FILE" | tee -a "$LOG_FILE"
echo "Batch size: $BATCH_SIZE" | tee -a "$LOG_FILE"
echo "===================================================================" | tee -a "$LOG_FILE"

python3 csv2vm.py "$CSV_FILE" --batch "$BATCH_SIZE" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=$?

echo "===================================================================" | tee -a "$LOG_FILE"
echo "Import finished at $(date) with exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "===================================================================" | tee -a "$LOG_FILE"

exit $EXIT_CODE


