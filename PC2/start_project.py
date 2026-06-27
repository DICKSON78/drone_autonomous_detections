#!/usr/bin/env python3
"""
start_project.py — Single terminal launcher for full drone stack.

Starts:
  1. Webots + PX4 bridge (PC2)
  2. Drone RADAR exporter on :8007 (PC3)
  3. Terminal GCS for interactive control
  4. QGC-ready MAVLink on :14550

Usage:
  cd PC2 && python3 start_project.py
"""

import os, sys, time, socket, subprocess, signal, threading

BASE = os.path.dirname(os.path.abspath(__file__))
PID_FILE = "/tmp/drone_project.pids"

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
CYAN = "\033[96m"; BOLD = "\033[1m"; NC = "\033[0m"

procs = []

def log(msg, color=GREEN):
    print(f"{color}[PROJECT]{NC} {msg}")

def check_port(host, port, timeout=1):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.send(b"")
        s.close()
        return True
    except:
        return False

def find_free_port(start):
    for p in range(start, start+100):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("0.0.0.0", p))
            s.close()
            return p
        except:
            pass
    return start

def launch(cmd, name, env=None):
    log(f"Starting {name}...", YELLOW)
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    p = subprocess.Popen(cmd, shell=True, env=full_env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    procs.append((p, name))
    return p

def cleanup(sig=None, frame=None):
    print("")
    log("Shutting down...", RED)
    for p, name in procs:
        if p.poll() is None:
            log(f"Stopping {name} (PID {p.pid})...")
            p.terminate()
            try:
                p.wait(timeout=5)
            except:
                p.kill()
    # Also clean orphan processes
    for name in ["px4_bridge.py", "webots-bin", "drone_exporter.py", "terminal_gcs.py"]:
        os.system(f"pkill -f '{name}' 2>/dev/null || true")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print(f"""
{CYAN}╔══════════════════════════════════════════════════════════╗{NC}
{CYAN}║{NC}  {BOLD}UDOM CIVE DRONE — FULL STACK LAUNCHER{NC}{CYAN}               ║{NC}
{CYAN}╠══════════════════════════════════════════════════════════╣{NC}
{CYAN}║{NC}  Starting all components...                            {CYAN}║{NC}
{CYAN}╚══════════════════════════════════════════════════════════╝{NC}
""")

    # Kill any existing processes
    for name in ["px4_bridge.py", "webots-bin", "drone_exporter.py"]:
        os.system(f"pkill -f '{name}' 2>/dev/null || true")
    time.sleep(1)

    # ── 1. Start Webots + bridge ──
    world = os.path.join(BASE, "webots", "worlds", "mavic2pro_px4.wbt")
    venv = os.path.join(BASE, "venv", "bin", "python3")
    snap = "/snap/webots/current"
    webots_bin = f"{snap}/usr/share/webots/bin/webots-bin"
    ld_path = f"{snap}/usr/share/webots/lib/webots:/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:{snap}/lib/x86_64-linux-gnu:{snap}/usr/lib/x86_64-linux-gnu"

    log("Starting Webots + MAVLink bridge...")
    env = {
        "PATH": f"{os.path.join(BASE, 'venv', 'bin')}:{os.environ.get('PATH', '')}",
        "WEBOTS_PYTHON": venv,
        "LD_LIBRARY_PATH": ld_path,
        "QT_QPA_PLATFORM": "wayland",
        "QT_QPA_PLATFORM_PLUGIN_PATH": f"{snap}/usr/share/webots/lib/webots/plugins/platforms",
        "DISPLAY": os.environ.get("DISPLAY", ":0"),
        "GIO_MODULE_DIR": "/dev/null",
    }
    launch(f"{webots_bin} --mode=realtime {world}", "Webots", env)

    # ── 2. Wait for bridge on :14550 ──
    log("Waiting for MAVLink bridge on UDP :14550...", YELLOW)
    started = False
    for i in range(120):
        time.sleep(2)
        if check_port("127.0.0.1", 14550):
            log("MAVLink bridge ready on :14550 ✓")
            started = True
            break
        if procs and procs[0][0].poll() is not None:
            log("Webots died early!", RED)
            cleanup()

    if not started:
        log("Bridge didn't start within 4 minutes.", RED)
        cleanup()
        return

    # ── 3. Start RADAR exporter on :8007 ──
    log("Starting Drone RADAR exporter...")
    exporter = os.path.join(BASE, "..", "PC3", "scripts", "drone_exporter.py")
    # The exporter hardcodes its path to mavlink_lite, might not work from PC2
    # Check if file exists first
    if os.path.exists(exporter):
        launch(f"python3 {exporter}", "RADAR Exporter")
        time.sleep(2)
        if check_port("127.0.0.1", 8007, timeout=2):
            log("RADAR ready on http://localhost:8007/radar ✓")
        else:
            log("RADAR port 8007 not responding — check logs", YELLOW)
    else:
        log(f"RADAR exporter not found at {exporter}", YELLOW)
        log("Install PC3 stack separately: cd PC3 && bash start_pc3.sh", YELLOW)

    # ── 4. Show combined info ──
    time.sleep(1)
    print(f"""
{CYAN}╔══════════════════════════════════════════════════════════╗{NC}
{CYAN}║{NC}  {BOLD}ALL SYSTEMS RUNNING{NC}{CYAN}                                   ║{NC}
{CYAN}╠══════════════════════════════════════════════════════════╣{NC}
{CYAN}║{NC}                                                      {CYAN}║{NC}
{CYAN}║{NC}  {BOLD}Terminal GCS{NC}  — use the terminal below to control     {CYAN}║{NC}
{CYAN}║{NC}  {BOLD}RADAR UI{NC}      — http://localhost:8007/radar           {CYAN}║{NC}
{CYAN}║{NC}  {BOLD}QGC{NC}           — connect to UDP :14550                 {CYAN}║{NC}
{CYAN}║{NC}  {BOLD}Metrics{NC}       — http://localhost:8007/metrics         {CYAN}║{NC}
{CYAN}║{NC}                                                      {CYAN}║{NC}
{CYAN}║{NC}  Press {BOLD}Ctrl+C{NC} to stop everything                        {CYAN}║{NC}
{CYAN}╚══════════════════════════════════════════════════════════╝{NC}
""")

    # ── 5. Launch Terminal GCS ──
    gcs_script = os.path.join(BASE, "webots", "controllers", "px4_bridge", "terminal_gcs.py")
    log("Launching Terminal GCS...")
    print(f"\n{GREEN}{'='*60}{NC}")
    print(f"{GREEN}  TERMINAL GCS — press a=arm  t=takeoff  l=land  q=quit{NC}")
    print(f"{GREEN}{'='*60}{NC}\n")

    # exec replaces this process with terminal_gcs.py
    os.execv(sys.executable, [sys.executable, gcs_script])

if __name__ == "__main__":
    main()
