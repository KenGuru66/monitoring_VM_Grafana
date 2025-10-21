#!/bin/bash
################################################################################
# Helper скрипт для установки min_interval в Grafana dashboard
# 
# Использование:
#   ./set_dashboard_interval.sh              # автоопределение из VictoriaMetrics
#   ./set_dashboard_interval.sh 1m           # установить конкретный интервал
#   ./set_dashboard_interval.sh --help       # справка
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_FILE="$SCRIPT_DIR/grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json"
VM_URL="${VM_URL:-http://localhost:8428}"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_help() {
    cat << EOF
Скрипт для установки min_interval в Grafana dashboard

Использование:
  $0                    # Автоматически определить интервал из VictoriaMetrics
  $0 <interval>         # Установить конкретный интервал (5s, 1m, 5m и т.д.)
  $0 --auto             # Автоопределение (то же что без параметров)
  $0 --help             # Эта справка

Примеры:
  $0                    # Автоопределение
  $0 5s                 # Для 5-секундных данных
  $0 1m                 # Для 1-минутных данных  
  $0 5m                 # Для 5-минутных данных

Переменные окружения:
  VM_URL               URL VictoriaMetrics (по умолчанию: $VM_URL)

EOF
}

function detect_interval_from_vm() {
    echo -e "${YELLOW}🔍 Определение scrape_interval из VictoriaMetrics...${NC}"
    
    # Получаем все уникальные значения scrape_interval
    INTERVALS=$(curl -s "${VM_URL}/api/v1/label/scrape_interval/values" | jq -r '.data[]' | sort -n)
    
    if [ -z "$INTERVALS" ]; then
        echo -e "${RED}❌ Не удалось получить scrape_interval из VictoriaMetrics${NC}"
        echo "Проверьте доступность VM: $VM_URL"
        exit 1
    fi
    
    # Подсчитываем количество разных интервалов
    INTERVAL_COUNT=$(echo "$INTERVALS" | wc -l)
    
    echo -e "${GREEN}✓ Найдено интервалов: $INTERVAL_COUNT${NC}"
    echo "$INTERVALS" | while read -r interval; do
        if [ "$interval" -lt 60 ]; then
            echo "  • ${interval}s"
        elif [ "$interval" -lt 3600 ]; then
            echo "  • $((interval / 60))m"
        else
            echo "  • $((interval / 3600))h"
        fi
    done
    
    if [ "$INTERVAL_COUNT" -eq 1 ]; then
        # Один интервал - используем его
        INTERVAL_SEC=$(echo "$INTERVALS" | head -1)
        convert_seconds_to_grafana_interval "$INTERVAL_SEC"
    else
        # Несколько интервалов - используем минимальный
        echo -e "${YELLOW}⚠️  Найдено несколько интервалов, используем минимальный${NC}"
        INTERVAL_SEC=$(echo "$INTERVALS" | head -1)
        convert_seconds_to_grafana_interval "$INTERVAL_SEC"
    fi
}

function convert_seconds_to_grafana_interval() {
    local seconds=$1
    
    if [ "$seconds" -lt 60 ]; then
        echo "${seconds}s"
    elif [ "$seconds" -lt 3600 ]; then
        echo "$((seconds / 60))m"
    else
        echo "$((seconds / 3600))h"
    fi
}

function set_interval() {
    local interval=$1
    
    echo -e "${YELLOW}📝 Установка min_interval = $interval в dashboard...${NC}"
    
    # Обновляем current value переменной min_interval
    jq --arg interval "$interval" '
      (.templating.list[] | select(.name == "min_interval") | .current) = {
        "selected": false,
        "text": $interval,
        "value": $interval
      }
      | (.templating.list[] | select(.name == "min_interval") | .options[] | select(.value == $interval)).selected = true
      | (.templating.list[] | select(.name == "min_interval") | .options[] | select(.value != $interval)).selected = false
      | .version = (.version + 1)
    ' "$DASHBOARD_FILE" > /tmp/dashboard_updated.json
    
    mv /tmp/dashboard_updated.json "$DASHBOARD_FILE"
    
    NEW_VERSION=$(jq '.version' "$DASHBOARD_FILE")
    echo -e "${GREEN}✓ Dashboard обновлен (версия: $NEW_VERSION)${NC}"
    echo -e "${GREEN}✓ min_interval установлен: $interval${NC}"
}

function restart_grafana() {
    echo -e "${YELLOW}🔄 Перезапуск Grafana...${NC}"
    
    cd "$SCRIPT_DIR"
    docker compose restart grafana > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Grafana перезапущена${NC}"
    else
        echo -e "${RED}❌ Ошибка перезапуска Grafana${NC}"
        exit 1
    fi
}

################################################################################
# Main
################################################################################

# Проверка аргументов
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    print_help
    exit 0
fi

echo "================================================================================"
echo "  🎯 Установка min_interval для Grafana Dashboard"
echo "================================================================================"

# Определение интервала
if [ -z "$1" ] || [ "$1" == "--auto" ]; then
    # Автоопределение
    INTERVAL=$(detect_interval_from_vm)
    echo -e "${GREEN}→ Определенный интервал: $INTERVAL${NC}"
else
    # Указан вручную
    INTERVAL="$1"
    echo -e "${GREEN}→ Установка интервала: $INTERVAL${NC}"
fi

# Валидация интервала
if ! echo "$INTERVAL" | grep -qE '^[0-9]+(s|m|h)$'; then
    echo -e "${RED}❌ Неверный формат интервала: $INTERVAL${NC}"
    echo "Ожидается формат: 5s, 1m, 5m, 1h и т.д."
    exit 1
fi

# Установка интервала
set_interval "$INTERVAL"

# Перезапуск Grafana
restart_grafana

echo "================================================================================"
echo -e "${GREEN}✅ ГОТОВО!${NC}"
echo ""
echo "Откройте dashboard и проверьте переменную \$min_interval в шапке:"
echo "  http://10.5.10.163:3000/d/huawei-oceanstor-real/"
echo ""
echo "Текущий min_interval: $INTERVAL"
echo "================================================================================"

