#!/bin/bash
# PC4 Build Frontend Script
# Builds React dashboard for production

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🔨 Building PC4 Web Dashboard..."
echo "=================================="

if [ ! -d "src/web-dashboard" ]; then
  echo "❌ Web dashboard directory not found"
  exit 1
fi

cd src/web-dashboard

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm ci
fi

# Build for production
echo "🏗️  Building production bundle..."
npm run build

if [ -d "dist" ]; then
  BUILD_SIZE=$(du -sh dist | cut -f1)
  FILE_COUNT=$(find dist -type f | wc -l)
  echo "✅ Build successful!"
  echo "   Build size: $BUILD_SIZE"
  echo "   Files: $FILE_COUNT"
else
  echo "❌ Build failed"
  exit 1
fi

echo ""
echo "Ready for deployment!"
