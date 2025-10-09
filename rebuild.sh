#!/bin/bash
# Quick rebuild script for updated containers

set -e

echo "════════════════════════════════════════════════════════════════"
echo "🔄 REBUILDING CONTAINERS"
echo "════════════════════════════════════════════════════════════════"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Stop services
echo "1️⃣  Stopping services..."
docker compose down
echo -e "${GREEN}✓ Services stopped${NC}"
echo ""

# Rebuild API
echo "2️⃣  Rebuilding API container (includes new routes + HTTP Range)..."
docker compose build --no-cache api
echo -e "${GREEN}✓ API rebuilt${NC}"
echo ""

# Rebuild Web
echo "3️⃣  Rebuilding Web container (includes CSV files table UI)..."
docker compose build --no-cache web
echo -e "${GREEN}✓ Web rebuilt${NC}"
echo ""

# Start services
echo "4️⃣  Starting services..."
docker compose up -d
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Wait for services to be ready
echo "5️⃣  Waiting for services to be ready..."
sleep 5

# Check API health
echo "6️⃣  Checking API health..."
for i in {1..10}; do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
    break
  fi
  if [ $i -eq 10 ]; then
    echo -e "${YELLOW}⚠️  API health check timeout${NC}"
  fi
  sleep 2
done
echo ""

# Show status
echo "7️⃣  Service status:"
docker compose ps
echo ""

# Show logs
echo "════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ REBUILD COMPLETE${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Test in browser: http://localhost:3001"
echo "  2. Upload ZIP with CSV mode"
echo "  3. Verify no Grafana button appears"
echo "  4. Check files table appears"
echo "  5. Test file download"
echo ""
echo "Or run automated test:"
echo "  ./test_csv_mode.sh test.zip"
echo ""
echo "To view logs:"
echo "  docker compose logs -f api"
echo "  docker compose logs -f web"
echo "════════════════════════════════════════════════════════════════"

