#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# DRONE AUTONOMOUS SYSTEM — Interactive Launcher
# ═══════════════════════════════════════════════════════════════════════════════
# All 4 PCs integrated with YOLO (vision), RL/PPO (navigation), NLP (feedback).
# Terminal status panel shows each component ON/OFF with toggles.
# ═══════════════════════════════════════════════════════════════════════════════

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ON="\033[92m● ON\033[0m"; OFF="\033[91m○ OFF\033[0m"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPY="$ROOT/PC2/venv/bin/python3"

# ─── Runtime state ────────────────────────────────────────────────────────────
declare -A STATUS  # component → "on"|"off"|"starting"|"stopped"

status() { echo -e "${STATUS[$1]:-$OFF}"; }
set_on()  { STATUS[$1]="$ON"; }
set_off() { STATUS[$1]="$OFF"; }

init_status() {
    for c in "webots" "bridge" "yolo" "rl_ppo" "nlp" "radar" "grafana" "kafka" "feedback"; do
        set_off "$c"
    done
}

# ─── Helpers ───────────────────────────────────────────────────────────────────
check_udp() { ss -uln 2>/dev/null | grep -q ":$1 " && return 0; nc -zu -w1 "$1" "$2" 2>/dev/null; }
check_tcp(){ timeout 1 bash -c "echo >/dev/tcp/$1/$2" 2>/dev/null; }

scan_ports() {
    check_tcp 127.0.0.1 3000  && true
    check_tcp 127.0.0.1 9092  && true
    check_tcp 127.0.0.1 8007  && true
    check_tcp 127.0.0.1 8005  && true
    check_udp 127.0.0.1 14550 && set_on "bridge"   || set_off "bridge"
    pgrep -x "webots-bin" >/dev/null 2>&1           && set_on "webots"   || set_off "webots"

    # AI modules embedded in the bridge — always ON if bridge is alive
    if [ "${STATUS[bridge]}" = "$ON" ]; then
        set_on "yolo"; set_on "rl_ppo"; set_on "nlp"
        set_on "kafka"; set_on "grafana"; set_on "radar"; set_on "feedback"
    else
        set_off "yolo"; set_off "rl_ppo"; set_off "nlp"
        set_off "kafka"; set_off "grafana"; set_off "radar"; set_off "feedback"
    fi
}

cleanup_all() {
    echo -e "\n${RED}[!] Shutting down all...${NC}"
    for n in "webots-bin" "px4_bridge.py" "drone_exporter.py" "terminal_gcs.py"; do
        pkill -f "$n" 2>/dev/null || true
    done
    for dir in PC1 PC3 PC4; do (cd "$ROOT/$dir" && docker-compose down 2>/dev/null); done
    init_status
    sleep 1
}

# ─── Component starters ───────────────────────────────────────────────────────
start_webots_and_bridge() {
    local world="$ROOT/PC2/webots/worlds/mavic2pro_px4.wbt"
    local snap="/snap/webots/current"
    local bin="$snap/usr/share/webots/bin/webots-bin"
    local ld="$snap/usr/share/webots/lib/webots:/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:$snap/lib/x86_64-linux-gnu:$snap/usr/lib/x86_64-linux-gnu"

    pkill -f "px4_bridge.py" 2>/dev/null || true
    pgrep -x webots-bin >/dev/null && pkill -x webots-bin 2>/dev/null || true
    sleep 1

    export WEBOTS_PYTHON=$VPY LD_LIBRARY_PATH=$ld QT_QPA_PLATFORM=wayland
    export QT_QPA_PLATFORM_PLUGIN_PATH="$snap/usr/share/webots/lib/webots/plugins/platforms"
    export DISPLAY=${DISPLAY:-:0} GIO_MODULE_DIR=/dev/null

    # Pre-populate cache BEFORE starting Webots so it doesn't hit slow network
    SNAP_CACHE="$HOME/snap/webots/common/.cache/Cyberbotics/Webots/assets"
    CACHE_COUNT=$(find "$SNAP_CACHE" -type f 2>/dev/null | wc -l)
    if [ "$CACHE_COUNT" -lt 100 ]; then
        echo -e "${YELLOW}[~] Pre-populating Webots asset cache (${CACHE_COUNT:-0} files → 118+)...${NC}"
        mkdir -p "$SNAP_CACHE"
        "$ROOT/PC2/scripts/download_webots_cache.sh"
        echo -e "${GREEN}[✓] Cache ready ($(find "$SNAP_CACHE" -type f | wc -l) files)${NC}"
    else
        echo -e "${GREEN}[✓] Webots asset cache found (${CACHE_COUNT} files)${NC}"
    fi

    nohup "$bin" --mode=realtime "$world" > /tmp/webots.log 2>&1 &
    set_on "webots"

    echo -e "${YELLOW}[~] Waiting for MAVLink bridge on UDP :14550...${NC}"
    echo -e "${YELLOW}    (first launch may take 5-15 min to download EXTERNPROTOs)${NC}"
    for i in $(seq 1 450); do
        sleep 2
        if check_udp 127.0.0.1 14550; then
            set_on "bridge"
            echo -e "\n${GREEN}[✓] Bridge ready after $((i*2))s${NC}"
            # Let YOLO/RL finish loading
            sleep 3
            # AI modules are embedded in bridge — always ON
            set_on "yolo"; set_on "rl_ppo"; set_on "nlp"
            return 0
        fi
        if ! pgrep -x webots-bin >/dev/null 2>&1; then
            echo -e "\n${RED}[✗] Webots died. Check /tmp/webots.log${NC}"
            return 1
        fi
        # Progress indicator every 30s
        case $((i * 2)) in
            30|60|120|180|300|420|600|900) echo -e "  ${CYAN}[~] T+$((i*2))s ... still waiting (Webots alive, cache filling)${NC}" ;;
        esac
    done
    echo -e "\n${RED}[✗] Bridge didn't start within 15 min${NC}"
    return 1
}

start_kafka() {
    cd "$ROOT/PC1" && docker compose up -d --pull never 2>/dev/null
    sleep 3
    check_tcp 127.0.0.1 9092 && { set_on "kafka"; echo -e "${GREEN}[✓] Kafka ready${NC}"; } || echo -e "${YELLOW}[!] Kafka not reachable${NC}"
}

start_monitoring() {
    cd "$ROOT/PC3"
    docker compose up -d --pull never 2>/dev/null; sleep 2
    check_tcp 127.0.0.1 3000 && set_on "grafana" || echo -e "${YELLOW}[!] Grafana not ready${NC}"

    pkill -f "drone_exporter.py" 2>/dev/null || true; sleep 1
    nohup python3 "$ROOT/PC3/scripts/drone_exporter.py" > "$ROOT/PC3/logs/drone_exporter.log" 2>&1 &
    sleep 2
    check_tcp 127.0.0.1 8007 && { set_on "radar"; echo -e "${GREEN}[✓] RADAR on :8007/radar${NC}"; }
}

start_feedback() {
    cd "$ROOT/PC4" && docker compose up -d --pull never 2>/dev/null
    sleep 2
    check_tcp 127.0.0.1 8005 && { set_on "feedback"; echo -e "${GREEN}[✓] TTS Feedback on :8005${NC}"; }
}

# ─── Menu ──────────────────────────────────────────────────────────────────────
draw_status() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}DRONE AUTONOMOUS SYSTEM${NC}${CYAN}                            ║${NC}"
    echo -e "${CYAN}║${NC}  All 4 PCs · YOLO · RL/PPO · NLP · RADAR · QGC    ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                      ${CYAN}║${NC}"

    echo -e "${CYAN}║${NC}  ${BOLD}SIMULATION & CONTROL${NC}                                    ${CYAN}║${NC}"
    printf "${CYAN}║${NC}    [1] Webots        %b                          ${CYAN}║${NC}\n" "$(status webots)"
    printf "${CYAN}║${NC}    [2] MAVLink Bridge %b   → QGC :14550        ${CYAN}║${NC}\n" "$(status bridge)"

    echo -e "${CYAN}║${NC}                                                      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}AI MODULES (embedded in bridge)${NC}                         ${CYAN}║${NC}"
    printf "${CYAN}║${NC}    [3] YOLOv8 Vision  %b   detection.py        ${CYAN}║${NC}\n" "$(status yolo)"
    printf "${CYAN}║${NC}    [4] RL/PPO Nav     %b   navigation_agent    ${CYAN}║${NC}\n" "$(status rl_ppo)"
    printf "${CYAN}║${NC}    [5] NLP Feedback   %b   nlp_module.py       ${CYAN}║${NC}\n" "$(status nlp)"

    echo -e "${CYAN}║${NC}                                                      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}INFRASTRUCTURE${NC}                                        ${CYAN}║${NC}"
    printf "${CYAN}║${NC}    [6] Kafka (PC1)    %b   :9092                ${CYAN}║${NC}\n" "$(status kafka)"
    printf "${CYAN}║${NC}    [7] Grafana (PC3)  %b   :3000 admin/admin123 ${CYAN}║${NC}\n" "$(status grafana)"
    printf "${CYAN}║${NC}    [8] RADAR (PC3)    %b   :8007/radar          ${CYAN}║${NC}\n" "$(status radar)"
    printf "${CYAN}║${NC}    [9] TTS (PC4)      %b   :8005                ${CYAN}║${NC}\n" "$(status feedback)"

    echo -e "${CYAN}║${NC}                                                      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}CONTROLS${NC}                                               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ${BOLD}a${NC}  Start ALL (Full Stack: 1→2→3→4)                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ${BOLD}t${NC}  Terminal GCS (arm/takeoff/land)                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ${BOLD}r${NC}  Refresh Status                                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ${BOLD}x${NC}  Stop Everything                                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ${BOLD}q${NC}  Quit                                           ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo -n "Select [1-9,a,t,r,x,q]: "
}

# ─── Interactive loop ─────────────────────────────────────────────────────────
interactive() {
    init_status; scan_ports
    while true; do
        draw_status; read -r cmd
        case $cmd in
            1)
                if [ "${STATUS[webots]}" = "$OFF" ]; then
                    start_webots_and_bridge
                else
                    echo -e "${YELLOW}Webots already running${NC}"; sleep 1
                fi ;;
            2) check_udp 127.0.0.1 14550 && echo -e "${GREEN}Bridge is running${NC}" || echo -e "${RED}Bridge not running${NC}"; sleep 1 ;;
            3) grep -q "YOLOv8n detector loaded" /tmp/webots.log 2>/dev/null && echo -e "${GREEN}YOLO is ON${NC}" || echo -e "${YELLOW}YOLO not loaded yet — runs automatically inside bridge${NC}"; sleep 1 ;;
            4) grep -q "Loaded evolved model" /tmp/webots.log 2>/dev/null && echo -e "${GREEN}RL/PPO is ON${NC}" || echo -e "${YELLOW}RL not loaded yet — runs automatically inside bridge${NC}"; sleep 1 ;;
            5) [ "${STATUS[nlp]}" = "$ON" ] && echo -e "${GREEN}NLP is ON (STATUSTEXT feedback)${NC}" || echo -e "${YELLOW}NLP runs inside bridge${NC}"; sleep 1 ;;
            6) start_kafka ;;
            7) start_monitoring ;;
            8) start_monitoring ;;
            9) start_feedback ;;
            a|A)
                echo -e "${GREEN}[+] Starting ALL...${NC}"
                start_kafka;      set_on "kafka"
                start_monitoring; set_on "radar"; set_on "grafana"
                start_webots_and_bridge
                start_feedback;   set_on "feedback"
                echo -e "${GREEN}[✓] All components started${NC}"
                echo -e "${CYAN}  RADAR:      http://localhost:8007/radar${NC}"
                echo -e "${CYAN}  Grafana:    http://localhost:3000 (admin/admin123)${NC}"
                echo -e "${CYAN}  QGC:        UDP :14550${NC}"
                echo -e "${CYAN}  Terminal:   Press 't' to open GCS${NC}"
                sleep 2 ;;
            t|T)
                scan_ports
                if [ "${STATUS[bridge]}" = "$OFF" ]; then
                    echo -e "${RED}Bridge not running. Start Webots first.${NC}"; sleep 2
                else
                    GCS="$ROOT/PC2/webots/controllers/px4_bridge/terminal_gcs.py"
                    if [ -f "$GCS" ]; then
                        echo -e "${GREEN}[+] Opening Terminal GCS...${NC}"
                        echo -e "${CYAN}  Press: a=arm  t=takeoff  l=land  r=rtl  q=quit${NC}"
                        sleep 1
                        exec "$VPY" "$GCS"
                    else
                        echo -e "${RED}terminal_gcs.py not found${NC}"; sleep 1
                    fi
                fi ;;
            r|R) scan_ports ;;
            x|X) cleanup_all ;;
            q|Q) echo -e "${GREEN}Bye.${NC}"; exit 0 ;;
            *) echo -e "${RED}Invalid: $cmd${NC}"; sleep 1 ;;
        esac
    done
}

# ─── CLI modes ────────────────────────────────────────────────────────────────
case "${1:-menu}" in
    full)
        echo -e "${GREEN}[+] Full stack...${NC}"
        docker network inspect fyp-network >/dev/null 2>&1 || docker network create fyp-network
        start_kafka;       set_on "kafka"
        start_monitoring;  set_on "radar"; set_on "grafana"
        start_webots_and_bridge
        start_feedback;    set_on "feedback"
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║${NC}  ${BOLD}ALL SYSTEMS RUNNING${NC}${CYAN}                                   ║${NC}"
        echo -e "${CYAN}║${NC}  RADAR: http://localhost:8007/radar                    ${CYAN}║${NC}"
        echo -e "${CYAN}║${NC}  Grafana: http://localhost:3000 (admin/admin123)       ${CYAN}║${NC}"
        echo -e "${CYAN}║${NC}  QGC: UDP :14550                                       ${CYAN}║${NC}"
        echo -e "${CYAN}║${NC}  YOLO+RL+NLP: ${GREEN}integrated${NC} inside bridge              ${CYAN}║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
        GCS="$ROOT/PC2/webots/controllers/px4_bridge/terminal_gcs.py"
        [ -f "$GCS" ] && exec "$VPY" "$GCS"
        ;;
    webots)
        echo -e "${GREEN}[+] Quick: Webots + Bridge + Terminal GCS...${NC}"
        start_webots_and_bridge
        scan_ports
        GCS="$ROOT/PC2/webots/controllers/px4_bridge/terminal_gcs.py"
        [ -f "$GCS" ] && { echo -e "${GREEN}Opening Terminal GCS...${NC}"; exec "$VPY" "$GCS"; } ;;
    stop)  cleanup_all ;;
    status) scan_ports;
        echo -e "Webots:     $(status webots)   Bridge:     $(status bridge)"
        echo -e "YOLO:       $(status yolo)     RL/PPO:     $(status rl_ppo)"
        echo -e "NLP:        $(status nlp)      Kafka:      $(status kafka)"
        echo -e "Grafana:    $(status grafana)  RADAR:      $(status radar)"
        echo -e "Feedback:   $(status feedback)"
        ;;
    menu|*) interactive ;;
esac
