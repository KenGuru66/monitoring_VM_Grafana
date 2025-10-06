#!/bin/bash
# Simple API test script

echo "🧪 Testing Huawei Monitoring API"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health check
echo "1️⃣  Testing API health..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "   ${GREEN}✅ PASS${NC} - API is healthy"
else
    echo -e "   ${RED}❌ FAIL${NC} - API is not responding"
    exit 1
fi
echo ""

# Test 2: Root endpoint
echo "2️⃣  Testing root endpoint..."
if curl -s http://localhost:8000/ | grep -q "Huawei Performance Data API"; then
    echo -e "   ${GREEN}✅ PASS${NC} - Root endpoint works"
else
    echo -e "   ${RED}❌ FAIL${NC} - Root endpoint failed"
    exit 1
fi
echo ""

# Test 3: Jobs endpoint
echo "3️⃣  Testing jobs list..."
if curl -s http://localhost:8000/api/jobs | grep -q "jobs"; then
    echo -e "   ${GREEN}✅ PASS${NC} - Jobs endpoint works"
else
    echo -e "   ${RED}❌ FAIL${NC} - Jobs endpoint failed"
    exit 1
fi
echo ""

# Test 4: API docs
echo "4️⃣  Testing API documentation..."
if curl -s http://localhost:8000/docs | grep -q "swagger"; then
    echo -e "   ${GREEN}✅ PASS${NC} - API docs available"
else
    echo -e "   ${RED}❌ FAIL${NC} - API docs not available"
    exit 1
fi
echo ""

# Test 5: Web UI
echo "5️⃣  Testing Web UI..."
if curl -s http://localhost:3001 | grep -q "root"; then
    echo -e "   ${GREEN}✅ PASS${NC} - Web UI is accessible"
else
    echo -e "   ${YELLOW}⚠️  WARN${NC} - Web UI may still be loading"
fi
echo ""

# Test 6: VictoriaMetrics
echo "6️⃣  Testing VictoriaMetrics..."
if curl -s http://localhost:8428/health 2>&1 | grep -q "OK"; then
    echo -e "   ${GREEN}✅ PASS${NC} - VictoriaMetrics is running"
else
    echo -e "   ${RED}❌ FAIL${NC} - VictoriaMetrics not responding"
fi
echo ""

# Test 7: Grafana
echo "7️⃣  Testing Grafana..."
if curl -s http://localhost:3000/api/health | grep -q "ok"; then
    echo -e "   ${GREEN}✅ PASS${NC} - Grafana is running"
else
    echo -e "   ${YELLOW}⚠️  WARN${NC} - Grafana may still be starting"
fi
echo ""

echo "=================================="
echo -e "${GREEN}✅ All critical tests passed!${NC}"
echo ""
echo "🌐 Access your services:"
echo "   Web UI:  http://localhost:3001"
echo "   API:     http://localhost:8000/docs"
echo "   Grafana: http://localhost:3000"
echo ""

