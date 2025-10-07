#!/bin/bash
# Скрипт очистки временных файлов от незавершенных процессов импорта

set -e

echo "=================================================="
echo "🧹 Cleanup Temporary Files"
echo "=================================================="
echo ""

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CLEANED=0

# 1. Очистка временных директорий от распаковки ZIP
echo "1. Cleaning temp extraction directories..."
if [ -d "temp_streaming_extract" ]; then
    SIZE=$(du -sh temp_streaming_extract 2>/dev/null | cut -f1)
    rm -rf temp_streaming_extract
    echo -e "   ${GREEN}✓ Removed temp_streaming_extract/ ($SIZE)${NC}"
    ((CLEANED++))
else
    echo "   ○ temp_streaming_extract/ - not found"
fi

# 2. Очистка временных файлов от распаковки .tgz
echo ""
echo "2. Cleaning temp decompression files..."
if [ -d "temp" ]; then
    TEMP_COUNT=$(find temp -type d -name "temp_*" 2>/dev/null | wc -l)
    if [ "$TEMP_COUNT" -gt 0 ]; then
        SIZE=$(du -sh temp 2>/dev/null | cut -f1)
        find temp -type d -name "temp_*" -exec rm -rf {} + 2>/dev/null || true
        echo -e "   ${GREEN}✓ Removed $TEMP_COUNT temp directories ($SIZE)${NC}"
        ((CLEANED++))
    else
        echo "   ○ No temp_* directories found"
    fi
else
    echo "   ○ temp/ - not found"
fi

# 3. Очистка nohup и log файлов от тестов
echo ""
echo "3. Cleaning test log files..."
LOG_FILES=(
    "nohup.out"
    "import_test.log"
)

for file in "${LOG_FILES[@]}"; do
    if [ -f "$file" ]; then
        SIZE=$(du -sh "$file" 2>/dev/null | cut -f1)
        rm -f "$file"
        echo -e "   ${GREEN}✓ Removed $file ($SIZE)${NC}"
        ((CLEANED++))
    fi
done

# 4. Очистка старых .pyc файлов
echo ""
echo "4. Cleaning Python cache..."
PYC_COUNT=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l)
if [ "$PYC_COUNT" -gt 0 ]; then
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete
    echo -e "   ${GREEN}✓ Removed $PYC_COUNT .pyc files${NC}"
    ((CLEANED++))
else
    echo "   ○ No .pyc files found"
fi

# 5. Очистка Docker volumes (опционально)
echo ""
echo "5. Checking Docker temporary volumes..."
DOCKER_TEMP=$(docker volume ls -q -f "dangling=true" 2>/dev/null | wc -l)
if [ "$DOCKER_TEMP" -gt 0 ]; then
    echo -e "   ${YELLOW}⚠ Found $DOCKER_TEMP dangling volumes${NC}"
    echo "   To clean: docker volume prune -f"
else
    echo "   ○ No dangling volumes"
fi

# 6. Проверка активных процессов импорта
echo ""
echo "6. Checking for running import processes..."
RUNNING=$(ps aux | grep -c "huawei_streaming_pipeline.py" | grep -v grep || echo "0")
if [ "$RUNNING" != "0" ]; then
    echo -e "   ${YELLOW}⚠ Found running import processes${NC}"
    echo "   To stop: pkill -f 'huawei_streaming_pipeline.py'"
else
    echo "   ○ No running import processes"
fi

# Итоги
echo ""
echo "=================================================="
echo "Summary"
echo "=================================================="

if [ "$CLEANED" -gt 0 ]; then
    echo -e "${GREEN}✓ Cleaned $CLEANED items${NC}"
else
    echo "○ Nothing to clean - system is already clean"
fi

# Показываем текущее использование диска
echo ""
echo "Current disk usage:"
df -h . | tail -1

echo ""
echo "✅ Cleanup completed!"

