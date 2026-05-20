#!/bin/bash
# Post-create setup for GitHub Codespaces
# Installs noVNC for browser-based Gazebo GUI access

set -e

echo "=== Setting up Gazebo Codespace ==="

# Install noVNC and Xvfb for virtual display
apt-get update
apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    python3-numpy \
    python3-opencv \
    x11-utils \
    mesa-utils \
    && rm -rf /var/lib/apt/lists/*

# Create noVNC index page
mkdir -p /usr/share/novnc
cat > /usr/share/novnc/index.html << 'HTML'
<!DOCTYPE html>
<html>
<head>
    <title>PX4 Gazebo Simulation</title>
    <meta charset="utf-8">
    <style>
        body { margin: 0; background: #1a1a2e; color: #eee; font-family: monospace; }
        #status { padding: 20px; text-align: center; }
        .ok { color: #4ade80; }
        .info { color: #60a5fa; }
    </style>
</head>
<body>
    <div id="status">
        <h2>PX4 Gazebo Simulation</h2>
        <p class="info">Click "Connect" to access the Gazebo GUI</p>
        <p class="info">Drone: gz_x500 | World: Dodoma, Tanzania</p>
        <p class="info">MAVLink: UDP 14550 (GCS) | UDP 14540 (SDK)</p>
    </div>
    <script src="vendor/pako/lib/zlib/inflate.js"></script>
    <script src="app/webutil.js"></script>
    <script>
        WebUtil.init_logging(WebUtil.getQueryVar('logging', 'warn'));
        document.title = 'PX4 Gazebo - ' + document.location.host;
        window.addEventListener('load', function() {
            WebUtil.loadTable();
            WebUtil.loadQueryVar();
            UI.start({ path: WebUtil.getQueryVar('path', '/vnc.html') });
        });
    </script>
</body>
</html>
HTML

# Create startup script
cat > /usr/local/bin/start-gazebo-gui.sh << 'SCRIPT'
#!/bin/bash
# Start virtual display and noVNC for Gazebo GUI

echo "Starting Xvfb on :1..."
Xvfb :1 -screen 0 1920x1080x24 &
sleep 2

echo "Starting x11vnc..."
x11vnc -display :1 -forever -nopw -listen localhost -rfbport 5900 &
sleep 2

echo "Starting noVNC websockify on port 6080..."
websockify --web /usr/share/novnc 6080 localhost:5900 &
sleep 2

echo "Starting Gazebo GUI..."
export DISPLAY=:1
gz sim -g &

echo ""
echo "=== Gazebo GUI Ready ==="
echo "Access the GUI at: http://localhost:6080/vnc.html"
echo "In Codespaces: Forward port 6080 and open in browser"
SCRIPT

chmod +x /usr/local/bin/start-gazebo-gui.sh

# Create convenience script for starting simulation
cat > /workspace/PC2/start_codespace.sh << 'SCRIPT'
#!/bin/bash
# Start PX4 + Gazebo in GitHub Codespaces

cd /workspace/PC2

echo "=== Starting PX4 Gazebo Simulation ==="

# Start PX4 SITL
echo "Starting PX4 SITL..."
px4 &
PX4_PID=$!

sleep 5

# Check if PX4 is running
if kill -0 $PX4_PID 2>/dev/null; then
    echo "✓ PX4 is running"
else
    echo "✗ PX4 failed to start"
    exit 1
fi

# Start Gazebo server (headless)
echo "Starting Gazebo server..."
gz sim -s -r &
GAZEBO_PID=$!

sleep 5

# Check if Gazebo is running
if kill -0 $GAZEBO_PID 2>/dev/null; then
    echo "✓ Gazebo server is running"
else
    echo "✗ Gazebo failed to start"
    exit 1
fi

echo ""
echo "=== Simulation Ready ==="
echo "MAVLink GCS: UDP 14550"
echo "MAVLink SDK: UDP 14540"
echo ""
echo "To start GUI (optional): start-gazebo-gui.sh"
echo "Then access at: http://localhost:6080/vnc.html"
echo ""

# Keep running
wait
SCRIPT

chmod +x /workspace/PC2/start_codespace.sh

echo ""
echo "=== Setup Complete ==="
echo "Run: /workspace/PC2/start_codespace.sh"
echo "For GUI: start-gazebo-gui.sh (then open port 6080 in browser)"
