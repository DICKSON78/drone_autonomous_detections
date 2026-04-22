#!/bin/bash
# PC4 Setup Nginx Script
# Installs and configures nginx on host machine

set -e

echo "🔧 PC4 Nginx Setup"
echo "=================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ This script must be run as root (use sudo)"
  exit 1
fi

# Detect OS
if command -v apt-get &> /dev/null; then
  # Ubuntu/Debian
  echo "📦 Installing nginx on Ubuntu/Debian..."
  apt-get update -qq
  apt-get install -y nginx
  
  CONFIG_DIR="/etc/nginx/sites-available"
elif command -v yum &> /dev/null; then
  # CentOS/RHEL
  echo "📦 Installing nginx on CentOS/RHEL..."
  yum install -y nginx
  
  CONFIG_DIR="/etc/nginx/conf.d"
elif command -v brew &> /dev/null; then
  # macOS
  echo "📦 Installing nginx on macOS..."
  brew install nginx
  
  CONFIG_DIR="/usr/local/etc/nginx/servers"
else
  echo "❌ Unsupported OS"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DASHBOARD_DIR="$PROJECT_DIR/src/web-dashboard"

if [ ! -f "$WEB_DASHBOARD_DIR/nginx.conf" ]; then
  echo "❌ nginx.conf not found at $WEB_DASHBOARD_DIR/nginx.conf"
  exit 1
fi

# Copy nginx configuration
echo "📝 Configuring nginx..."
cp "$WEB_DASHBOARD_DIR/nginx.conf" "$CONFIG_DIR/pc4-dashboard" 2>/dev/null || \
  cp "$WEB_DASHBOARD_DIR/nginx.conf" "$CONFIG_DIR/pc4.conf"

# Create log directory
mkdir -p "$PROJECT_DIR/logs"
chmod 755 "$PROJECT_DIR/logs"

# Test nginx configuration
nginx -t

# Enable and start nginx
echo "🚀 Starting nginx..."
if command -v systemctl &> /dev/null; then
  systemctl enable nginx
  systemctl restart nginx
  echo "✅ nginx started and enabled for auto-start"
else
  nginx
  echo "✅ nginx started"
fi

echo ""
echo "Setup complete! Visit http://localhost to access the dashboard"
