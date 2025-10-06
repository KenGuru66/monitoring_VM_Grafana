#!/bin/bash
# Build and run Huawei Monitoring Stack with Web UI

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Huawei Storage Monitoring - Web Stack Builder          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose found"
echo ""

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose down 2>/dev/null || true
echo ""

# Build services
echo "🏗️  Building services (this may take 2-5 minutes)..."
docker-compose build --pull
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d
echo ""

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check status
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""

# Health checks
echo "🏥 Health Checks:"

# Check API
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✅ API: http://localhost:8000"
else
    echo "  ⚠️  API: Not ready yet (may need a few more seconds)"
fi

# Check Web
if curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo "  ✅ Web UI: http://localhost:3001"
else
    echo "  ⚠️  Web UI: Not ready yet (may need a few more seconds)"
fi

# Check Grafana
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "  ✅ Grafana: http://localhost:3000"
else
    echo "  ⚠️  Grafana: Not ready yet (may need a few more seconds)"
fi

# Check VictoriaMetrics
if curl -s http://localhost:8428/health > /dev/null 2>&1; then
    echo "  ✅ VictoriaMetrics: http://localhost:8428"
else
    echo "  ⚠️  VictoriaMetrics: Not ready yet (may need a few more seconds)"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ Stack is running!                                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Access Web UI:        http://localhost:3001"
echo "📖 API Documentation:    http://localhost:8000/docs"
echo "📊 Grafana Dashboard:    http://localhost:3000"
echo "                         (admin / changeme)"
echo ""
echo "📝 View logs:            docker-compose logs -f"
echo "🛑 Stop services:        docker-compose down"
echo ""
echo "Happy monitoring! 🎉"
