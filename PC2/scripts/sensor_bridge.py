#!/usr/bin/env python3
"""Sensor Bridge — MAVLink telemetry logger and HTTP server."""

import os, sys, time, json, csv, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mavlink_lite import DroneConnection

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"; RESET = "\033[0m"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

latest_telemetry = {}
telemetry_lock = threading.Lock()

class TelemetryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        with telemetry_lock:
            data = json.dumps(latest_telemetry, indent=2)
        self.wfile.write(data.encode())

    def log_message(self, format, *args):
        pass

class SensorBridge:
    def __init__(self, host="127.0.0.1", port=14550, http_port=8090):
        self.host = host
        self.port = port
        self.http_port = http_port
        self.drone = None
        self.running = True
        self.csv_writer = None
        self.csv_file = None
        self.log_path = os.path.join(LOG_DIR,
            f"telemetry_{time.strftime('%Y%m%d_%H%M%S')}.csv")

    def connect(self):
        self.drone = DroneConnection((self.host, self.port))
        self.drone.connect()
        for i in range(10):
            t = self.drone.get_telemetry()
            if t["connected"]:
                return True
            time.sleep(1)
        return False

    def setup_csv_logging(self):
        self.csv_file = open(self.log_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            "timestamp", "lat", "lon", "alt", "heading",
            "armed", "mode", "battery", "voltage",
            "roll", "pitch", "vel_x", "vel_y", "vel_z",
            "satellites", "fix_type"
        ])
        self.csv_file.flush()

    def log_telemetry(self):
        t = self.drone.get_telemetry()
        row = [
            time.time(),
            t.get("lat", 0), t.get("lon", 0), t.get("alt", 0),
            t.get("heading", 0),
            1 if t.get("armed") else 0,
            t.get("mode", "?"),
            t.get("battery", -1), t.get("voltage", 0),
            t.get("roll", 0), t.get("pitch", 0),
            t.get("vel_x", 0), t.get("vel_y", 0), t.get("vel_z", 0),
            t.get("satellites", 0), t.get("fix_type", 0),
        ]
        if self.csv_writer:
            self.csv_writer.writerow(row)
            self.csv_file.flush()
        with telemetry_lock:
            latest_telemetry.clear()
            latest_telemetry.update(t)
            latest_telemetry["timestamp"] = time.time()

    def start_http_server(self):
        server = HTTPServer(("0.0.0.0", self.http_port), TelemetryHandler)
        server.serve_forever()

    def run(self):
        if not self.connect():
            print(f"  {RED}[BRIDGE] Connection failed{RESET}")
            return
        print(f"  {GREEN}[BRIDGE] Connected ✓{RESET}")
        self.setup_csv_logging()
        print(f"  {GREEN}[BRIDGE] Logging to: {self.log_path}{RESET}")
        http_thread = threading.Thread(target=self.start_http_server, daemon=True)
        http_thread.start()
        print(f"  {GREEN}[BRIDGE] HTTP telemetry at :{self.http_port}{RESET}")
        while self.running:
            try:
                self.log_telemetry()
                time.sleep(0.5)
            except:
                break
        if self.csv_file:
            self.csv_file.close()
        if self.drone:
            self.drone.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sensor Telemetry Bridge")
    parser.add_argument("host", nargs="?", default="127.0.0.1")
    parser.add_argument("port", nargs="?", type=int, default=14550)
    parser.add_argument("--http-port", type=int, default=8090)
    args = parser.parse_args()
    bridge = SensorBridge(args.host, args.port, args.http_port)
    try:
        bridge.run()
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}[BRIDGE] Stopped{RESET}")
        bridge.running = False

if __name__ == "__main__":
    main()
