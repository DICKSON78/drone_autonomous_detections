#!/bin/bash
# Post-create setup for GitHub Codespaces (DEVELOPMENT ONLY)
# Webots must be installed on the host machine natively.

set -e

echo "=== Setting up Webots Development Environment ==="

# Install Python dependencies for the project
pip3 install --quiet numpy opencv-python pyyaml influxdb-client 2>/dev/null || true

echo ""
echo "=== Webots Development Environment Ready ==="
echo ""
echo "IMPORTANT: Webots is NOT available inside this container."
echo "Webots must be installed on your HOST machine at /usr/local/webots"
echo ""
echo "To run locally (outside container):"
echo "  cd PC2 && bash start_webots.sh"
echo ""
echo "For codespaces: Install Webots on the host and forward port 14550"
