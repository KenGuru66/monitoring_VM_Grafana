#!/bin/bash
# Скрипт диагностики здоровья системы мониторинга

set -e

echo "=================================================="
echo "🏥 Health Check: Monitoring System"
echo "=================================================="
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция проверки
check_service() {
    local service_name=$1
    local container_name=$2
    
    echo -n "Checking $service_name... "
    
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        status=$(docker inspect --format='{{.State.Status}}' "$container_name")
        if [ "$status" = "running" ]; then
            echo -e "${GREEN}✓ Running${NC}"
            return 0
        else
            echo -e "${RED}✗ Stopped (status: $status)${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Not found${NC}"
        return 1
    fi
}

# Функция проверки сетевой доступности (через HTTP, т.к. ping может быть недоступен)
check_network() {
    local from_container=$1
    local to_host=$2
    local port=$3
    local service_name=$4
    
    echo -n "  Network: $from_container → $to_host:$port... "
    
    # Используем curl вместо ping (более надежно в Docker)
    if docker exec "$from_container" sh -c "command -v curl > /dev/null" 2>/dev/null; then
        if docker exec "$from_container" curl -sf --max-time 2 "http://${to_host}:${port}/" > /dev/null 2>&1 || \
           docker exec "$from_container" curl -sf --max-time 2 "http://${to_host}:${port}/-/healthy" > /dev/null 2>&1 || \
           docker exec "$from_container" curl -sf --max-time 2 "http://${to_host}:${port}/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Reachable${NC}"
            return 0
        else
            echo -e "${RED}✗ Unreachable${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}? curl not available${NC}"
        return 0
    fi
}

# Функция проверки HTTP endpoint
check_http() {
    local container_name=$1
    local url=$2
    local service_name=$3
    
    echo -n "  HTTP: $url... "
    
    if docker exec "$container_name" curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

echo "1. Container Status"
echo "-------------------"
check_service "VictoriaMetrics" "monitoring_vm_grafana-victoriametrics-1"
VM_STATUS=$?

check_service "VMAgent" "monitoring_vm_grafana-vmagent-1"
VMAGENT_STATUS=$?

check_service "Grafana" "monitoring_vm_grafana-grafana-1"
GRAFANA_STATUS=$?

check_service "API" "monitoring_vm_grafana-api-1"
API_STATUS=$?

check_service "Web" "monitoring_vm_grafana-web-1"
WEB_STATUS=$?

echo ""
echo "2. Network Connectivity"
echo "----------------------"

if [ $API_STATUS -eq 0 ]; then
    check_network "monitoring_vm_grafana-api-1" "victoriametrics" "8428" "VictoriaMetrics"
    check_network "monitoring_vm_grafana-api-1" "vmagent" "8429" "VMAgent"
fi

echo ""
echo "3. Service Health"
echo "----------------"

if [ $VMAGENT_STATUS -eq 0 ]; then
    check_http "monitoring_vm_grafana-api-1" "http://vmagent:8429/-/healthy" "VMAgent Health"
fi

if [ $VM_STATUS -eq 0 ]; then
    check_http "monitoring_vm_grafana-api-1" "http://victoriametrics:8428/health" "VictoriaMetrics Health"
fi

if [ $GRAFANA_STATUS -eq 0 ]; then
    check_http "monitoring_vm_grafana-grafana-1" "http://localhost:3000/api/health" "Grafana Health"
fi

echo ""
echo "4. Docker Network"
echo "----------------"
NETWORK_NAME="monitoring_vm_grafana_monitoring"

if docker network inspect "$NETWORK_NAME" &> /dev/null; then
    echo -e "Network '$NETWORK_NAME': ${GREEN}✓ Exists${NC}"
    
    CONTAINERS=$(docker network inspect "$NETWORK_NAME" --format='{{len .Containers}}')
    echo "  Containers connected: $CONTAINERS"
    
    echo "  Container IPs:"
    docker network inspect "$NETWORK_NAME" --format='{{range .Containers}}    - {{.Name}}: {{.IPv4Address}}{{println}}{{end}}'
else
    echo -e "Network '$NETWORK_NAME': ${RED}✗ Not found${NC}"
fi

echo ""
echo "5. Recent Errors"
echo "---------------"

echo "Checking API logs for errors (last 10)..."
if [ $API_STATUS -eq 0 ]; then
    ERROR_COUNT=$(docker logs monitoring_vm_grafana-api-1 --tail 100 2>&1 | grep -c "ERROR" || true)
    DNS_ERROR_COUNT=$(docker logs monitoring_vm_grafana-api-1 --tail 100 2>&1 | grep -c "Failed to resolve" || true)
    
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠ Found $ERROR_COUNT errors in recent logs${NC}"
        if [ "$DNS_ERROR_COUNT" -gt 0 ]; then
            echo -e "  ${RED}⚠ Found $DNS_ERROR_COUNT DNS resolution errors${NC}"
        fi
        
        echo ""
        echo "  Recent errors:"
        docker logs monitoring_vm_grafana-api-1 --tail 100 2>&1 | grep "ERROR" | tail -5 | sed 's/^/    /'
    else
        echo -e "  ${GREEN}✓ No recent errors${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ Cannot check (API not running)${NC}"
fi

echo ""
echo "=================================================="
echo "Summary"
echo "=================================================="

TOTAL_CHECKS=5
PASSED=0

[ $VM_STATUS -eq 0 ] && ((PASSED++))
[ $VMAGENT_STATUS -eq 0 ] && ((PASSED++))
[ $GRAFANA_STATUS -eq 0 ] && ((PASSED++))
[ $API_STATUS -eq 0 ] && ((PASSED++))
[ $WEB_STATUS -eq 0 ] && ((PASSED++))

echo "Services: $PASSED/$TOTAL_CHECKS running"

if [ $PASSED -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}✓ All systems operational${NC}"
    exit 0
elif [ $PASSED -gt 0 ]; then
    echo -e "${YELLOW}⚠ Some services have issues${NC}"
    echo ""
    echo "To restart all services:"
    echo "  docker-compose restart"
    exit 1
else
    echo -e "${RED}✗ Critical: No services running${NC}"
    echo ""
    echo "To start all services:"
    echo "  docker-compose up -d"
    exit 2
fi

