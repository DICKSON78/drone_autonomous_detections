#!/bin/bash
# PC4 Run Tests Script
# Runs all test suites

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🧪 Running PC4 Test Suites"
echo "=========================="

FAILED=0

# Test Feedback Service
if [ -d "src/feedback-service" ]; then
  echo ""
  echo "Testing Feedback Service..."
  cd "$PROJECT_DIR/src/feedback-service"
  
  if [ -f "requirements.txt" ]; then
    # Install test dependencies
    pip install -q pytest httpx 2>/dev/null || true
    
    if [ -d "tests" ]; then
      python -m pytest tests/ -v || FAILED=$((FAILED + 1))
    fi
  fi
fi

# Test WebSocket Server
if [ -d "src/websocket-server" ]; then
  echo ""
  echo "Testing WebSocket Server..."
  cd "$PROJECT_DIR/src/websocket-server"
  
  if [ -f "package.json" ]; then
    if [ ! -d "node_modules" ]; then
      npm ci > /dev/null 2>&1
    fi
    
    if [ -d "tests" ]; then
      npm test || FAILED=$((FAILED + 1))
    fi
  fi
fi

# Test Web Dashboard
if [ -d "src/web-dashboard" ]; then
  echo ""
  echo "Testing Web Dashboard..."
  cd "$PROJECT_DIR/src/web-dashboard"
  
  if [ -f "package.json" ]; then
    if [ ! -d "node_modules" ]; then
      npm ci > /dev/null 2>&1
    fi
    
    npm test -- --passWithNoTests || FAILED=$((FAILED + 1))
  fi
fi

echo ""
echo "=========================="
if [ $FAILED -eq 0 ]; then
  echo "✅ All tests passed!"
  exit 0
else
  echo "❌ $FAILED test suite(s) failed"
  exit 1
fi
