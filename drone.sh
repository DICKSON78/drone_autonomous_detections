#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  DRONE COMMAND CENTER — Unified Launcher
#  Single script to control the entire drone ecosystem.
#  Run:  ./drone.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ─── Colors ─────────────────────────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'
B='\033[1m'; D='\033[2m'; N='\033[0m'

ON="${G}● ONLINE${N}"; OFF="${R}○ OFFLINE${N}"; WARN="${Y}◐ WAITING${N}"

# ─── State ──────────────────────────────────────────────────────────────────────
declare -A STAT
ping_svc() {
    local svc=$1 port=$2
    if timeout 1 bash -c "echo >/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
        STAT[$svc]="$ON"
    else
        STAT[$svc]="$OFF"
    fi
}
ping_udp() { ss -uln 2>/dev/null | grep -q ":$1 " && STAT["$2"]="$ON" || STAT["$2"]="$OFF"; }
ping_proc() {
    if pgrep -f "$2" >/dev/null 2>&1; then STAT["$1"]="$ON"; else STAT["$1"]="$OFF"; fi
}

scan() {
    ping_svc "backend"  8007
    ping_svc "grafana"  3000
    ping_svc "prom"     9090
    ping_udp "14550"    "bridge"
    ping_proc "webots"  "webots-bin"
    ping_proc "qgc"     "QGroundControl.AppImage"
    ping_proc "desktop" "electron.*PC3/desktop"
}

# ─── Docker Helpers ─────────────────────────────────────────────────────────────
dkr_up() {
    echo -e "${C}[+] Starting Docker services...${N}"
    # Remove conflicting containers from old PC3 compose
    for c in pc3-backend grafana prometheus node-exporter influxdb postgres api-gateway telemetry-collector; do
        docker rm -f "$c" 2>/dev/null || true
    done
    docker compose up -d --remove-orphans 2>/dev/null || docker compose up -d
    echo -e "${G}[✓] Docker services started${N}"
}
dkr_down() {
    echo -e "${R}[!] Stopping Docker services...${N}"
    docker compose down 2>/dev/null || true
    echo -e "${R}[✓] Docker services stopped${N}"
}
dkr_build() {
    echo -e "${Y}[~] Building Docker images...${N}"
    docker compose build --no-cache
    echo -e "${G}[✓] Build complete${N}"
}

# ─── Component starters ─────────────────────────────────────────────────────────
start_webots() {
    if [ "${STAT[webots]}" = "$ON" ]; then
        echo -e "${Y}[!] Webots already running${N}"; sleep 1; return
    fi
    local world="$ROOT/PC2/webots/worlds/mavic2pro_px4.wbt"
    local snap="/snap/webots/current"
    local bin="$snap/usr/share/webots/bin/webots-bin"

    if [ ! -f "$bin" ]; then
        echo -e "${R}[✗] Webots not installed. Run: sudo snap install webots${N}"
        sleep 2; return
    fi

    pkill -f "px4_bridge.py" 2>/dev/null || true

    export WEBOTS_PYTHON="$ROOT/PC2/venv/bin/python3" \
           LD_LIBRARY_PATH="$snap/usr/share/webots/lib/webots:/lib/x86_64-linux-gnu" \
           DISPLAY="${DISPLAY:-:0}" \
           QT_QPA_PLATFORM="${WAYLAND_DISPLAY:+wayland}${WAYLAND_DISPLAY:-xcb}"

    # Pre-populate cache
    local cache="$HOME/snap/webots/common/.cache/Cyberbotics/Webots/assets"
    if [ "$(find "$cache" -type f 2>/dev/null | wc -l)" -lt 100 ]; then
        echo -e "${Y}[~] Caching Webots assets (first launch may be slow)...${N}"
        mkdir -p "$cache"
        bash "$ROOT/PC2/scripts/download_webots_cache.sh" 2>/dev/null || true
    fi

    nohup "$bin" --mode=realtime "$world" > /tmp/webots.log 2>&1 &
    echo -e "${G}[✓] Webots launched${N}"
    echo -e "${D}    Waiting for bridge on UDP :14550...${N}"

    for i in $(seq 1 120); do
        sleep 2
        if ss -uln 2>/dev/null | grep -q ":14550 "; then
            echo -e "${G}[✓] Bridge ready after $((i*2))s${N}"
            scan; return 0
        fi
        [ $((i*2)) -eq 30 ] && echo -e "${D}    Still waiting... (Webots loading EXTERNPROTOs)${N}"
        [ $((i*2)) -eq 120 ] && echo -e "${D}    Still waiting... (check /tmp/webots.log)${N}"
    done
    echo -e "${R}[✗] Bridge not ready within 4min. Check /tmp/webots.log${N}"
}

start_qgc() {
    local qgc="$ROOT/QGroundControl.AppImage"
    if [ ! -f "$qgc" ]; then
        echo -e "${Y}[~] QGroundControl not found — downloading...${N}"
        local url="https://github.com/mavlink/qgroundcontrol/releases/download/v5.0.8/QGroundControl-x86_64.AppImage"
        wget -q --show-progress -O "$qgc" "$url" 2>/dev/null || curl -#Lo "$qgc" "$url" 2>/dev/null || {
            echo -e "${R}[✗] Download failed. Get it manually:${N}"
            echo -e "${D}    https://docs.qgroundcontrol.com${N}"
            sleep 2; return
        }
        chmod +x "$qgc"
        echo -e "${G}[✓] Downloaded to $qgc${N}"
    fi
    nohup "$qgc" --appimage-extract-and-run > /tmp/qgc.log 2>&1 &
    echo -e "${G}[✓] QGroundControl launched${N}"
}

open_dash() {
    echo -e "${C}[+] Opening Drone Dashboard...${N}"
    xdg-open "http://localhost:8007" 2>/dev/null || \
        python3 -m webbrowser "http://localhost:8007" 2>/dev/null || \
        echo -e "${Y}    Open: http://localhost:8007${N}"
}

open_grafana() {
    echo -e "${C}[+] Opening Grafana...${N}"
    xdg-open "http://localhost:3000" 2>/dev/null || \
        echo -e "${Y}    Open: http://localhost:3000 (admin/admin123)${N}"
}

start_gcs() {
    local gcs="$ROOT/PC2/webots/controllers/px4_bridge/terminal_gcs.py"
    if [ ! -f "$gcs" ]; then
        echo -e "${R}[✗] terminal_gcs.py not found${N}"; sleep 1; return
    fi
    echo -e "${C}[+] Terminal GCS${N}"
    echo -e "${D}    a=arm  t=takeoff  l=land  r=rtl  q=quit${N}"
    sleep 1
    python3 "$gcs"
}

start_desktop() {
    local dir="$ROOT/PC3/desktop"
    if [ ! -f "$dir/node_modules/.package-lock.json" ]; then
        echo -e "${Y}[~] Installing Electron dependencies...${N}"
        (cd "$dir" && npm install) || {
            echo -e "${R}[✗] npm install failed${N}"; sleep 1; return
        }
    fi
    if pgrep -f "electron.*PC3/desktop" >/dev/null 2>&1; then
        echo -e "${Y}[!] Desktop App already running${N}"
        scan; return
    fi
    echo -e "${C}[+] Launching Desktop App...${N}"
    (cd "$dir" && nohup npx electron . --no-sandbox > /tmp/desktop.log 2>&1 &)
    for i in $(seq 1 10); do
        sleep 1
        pgrep -f "electron.*PC3/desktop" >/dev/null 2>&1 && break
    done
    scan
}

show_logs() {
    local f=$1 label=$2
    if [ -f "$f" ]; then
        echo -e "${C}─── $label ───${N}"
        tail -20 "$f"
    else
        echo -e "${D}    No $label log found${N}"
    fi
}

# ─── Header ─────────────────────────────────────────────────────────────────────
header() {
    local w=68
    local c="\033[0;36m" n="\033[0m" b="\033[1m" d="\033[2m"

    echo -e "${c}╔$(printf '═%.0s' $(seq 1 $w))╗${n}"
    echo -e "${c}║${n}           ${b}██████╗ ██████╗  ██████╗ ███╗   ██╗███████╗${n}          ${c}║${n}"
    echo -e "${c}║${n}           ${b}██╔══██╗██╔══██╗██╔═══██╗████╗  ██║██╔════╝${n}          ${c}║${n}"
    echo -e "${c}║${n}           ${b}██║  ██║██████╔╝██║   ██║██╔██╗ ██║█████╗${n}  ${d}v2.0${n}  ${c}║${n}"
    echo -e "${c}║${n}           ${b}██║  ██║██╔══██╗██║   ██║██║╚██╗██║██╔══╝${n}          ${c}║${n}"
    echo -e "${c}║${n}           ${b}██████╔╝██║  ██║╚██████╔╝██║ ╚████║███████╗${n}          ${c}║${n}"
    echo -e "${c}║${n}           ${b}╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝${n}          ${c}║${n}"
    echo -e "${c}║${n}                    ${d}Command Center${n}                              ${c}║${n}"
    echo -e "${c}╠$(printf '═%.0s' $(seq 1 $w))╣${n}"
}

# ─── Draw Menu ──────────────────────────────────────────────────────────────────
menu() {
    scan
    echo -e "${C}╔══════════════════════════════════════════════════════════════════╗${N}"
    echo -e "${C}║${N}  ${B}[01]${N}  Start Docker Services    ${STAT[backend]:-$OFF}    ${STAT[grafana]:-$OFF}    ${STAT[prom]:-$OFF}  ${C}║${N}"
    echo -e "${C}║${N}  ${B}[02]${N}  Launch Webots            ${STAT[webots]:-$OFF}                         ${C}║${N}"
    echo -e "${C}║${N}  ${B}[03]${N}  Open Web Dashboard       ${C}→${N} http://localhost:8007       ${C}║${N}"
    echo -e "${C}║${N}  ${B}[04]${N}  Launch QGroundControl    ${STAT[qgc]:-$OFF}                         ${C}║${N}"
    echo -e "${C}║${N}  ${B}[05]${N}  Open Grafana             ${C}→${N} http://localhost:3000       ${C}║${N}"
    echo -e "${C}║${N}  ${B}[06]${N}  Terminal GCS             ${D}(arm/takeoff/land)${N}           ${C}║${N}"
    echo -e "${C}║${N}  ${B}[07]${N}  Show Logs                ${D}(backend/webots)${N}             ${C}║${N}"
    echo -e "${C}║${N}  ${B}[08]${N}  Launch Desktop App       ${STAT[desktop]:-$OFF}                         ${C}║${N}"
    echo -e "${C}╠══════════════════════════════════════════════════════════════════╣${N}"
    echo -e "${C}║${N}  ${B}[b]${N}   Rebuild Docker Image      ${D}(after code changes)${N}          ${C}║${N}"
    echo -e "${C}║${N}  ${B}[x]${N}   Stop All                  ${D}(docker + processes)${N}          ${C}║${N}"
    echo -e "${C}║${N}  ${B}[q]${N}   Quit                                              ${C}║${N}"
    echo -e "${C}╚══════════════════════════════════════════════════════════════════╝${N}"
    echo -n "  Select: "
}

# ─── Interactive Loop ───────────────────────────────────────────────────────────
interactive() {
    clear

    # Check Docker
    if ! docker info >/dev/null 2>&1; then
        echo -e "${R}[✗] Docker not running. Start Docker first.${N}"
        echo -e "${D}    sudo systemctl start docker${N}"
        exit 1
    fi

    header
    while true; do
        menu
        read -r cmd
        case $cmd in
            1)  dkr_up
                sleep 2
                scan ;;
            2)  start_webots
                scan ;;
            3)  open_dash ;;
            4)  start_qgc
                scan ;;
            5)  open_grafana ;;
            6)  start_gcs ;;
            7)  show_logs /tmp/server.log   "Backend (server.log)"
                echo
                show_logs /tmp/webots.log   "Webots"
                echo
                show_logs /tmp/server4.log  "Backend (alt)"
                echo -e "\n${D}Press Enter to continue...${N}"
                read -r ;;
            8)  start_desktop ;;
            b|B) dkr_down
                dkr_build
                dkr_up
                scan ;;
            x|X) dkr_down
                pkill -f "px4_bridge.py|webots-bin|QGroundControl.AppImage|electron.*PC3/desktop" 2>/dev/null || true
                echo -e "${G}[✓] All stopped${N}" ;;
            q|Q) echo -e "${G}Bye.${N}"; exit 0 ;;
            *)  echo -e "${R}Invalid: $cmd${N}"; sleep 1
                echo -e "${D}Press Enter to continue...${N}"
                read -r ;;
        esac
    done
}

# ─── CLI Mode ───────────────────────────────────────────────────────────────────
case "${1:-menu}" in
    up)     dkr_up ;;
    down)   dkr_down ;;
    build)  dkr_build ;;
    logs)
        show_logs /tmp/server.log "Backend"
        show_logs /tmp/webots.log "Webots"
        ;;
    menu|*) interactive ;;
esac
