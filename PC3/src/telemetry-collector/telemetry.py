"""
Telemetry Collector — bridges MAVLink telemetry to InfluxDB and exposes REST API.
Consumes drone telemetry via MAVLink UDP, writes to InfluxDB, serves /health and /metrics.
"""

import os, sys, time, json, threading, socket, struct
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, '/home/dickson/FYP/drone_autonomous/PC2/scripts')
from mavlink_lite import DroneConnection

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    INFLUX_AVAILABLE = True
except ImportError:
    INFLUX_AVAILABLE = False

# ── Configuration ──
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'drone-telemetry-token')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'drone-project')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'drone_telemetry')
MAVLINK_HOST = os.getenv('MAVLINK_HOST', '127.0.0.1')
MAVLINK_PORT = int(os.getenv('MAVLINK_PORT', '14550'))
PORT = int(os.getenv('PORT', '8004'))

# ── State ──
telemetry_cache = {
    "connected": False, "armed": False, "mode": "UNKNOWN",
    "lat": 0.0, "lon": 0.0, "alt": 0.0, "battery": 0.0,
    "heading": 0.0, "speed": 0.0, "satellites": 0, "fix_type": 0,
    "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
    "vel_x": 0.0, "vel_y": 0.0, "vel_z": 0.0,
    "timestamp": None
}
metrics_count = {"gps_points": 0, "battery_points": 0, "attitude_points": 0}

# ── InfluxDB Client ──
influx_client = None
write_api = None
if INFLUX_AVAILABLE:
    try:
        influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        write_api = influx_client.write_api()
        print(f"[telemetry] InfluxDB connected: {INFLUXDB_URL}")
    except Exception as e:
        print(f"[telemetry] InfluxDB unavailable: {e}")


def write_to_influx(measurement, fields, tags=None):
    """Write a data point to InfluxDB."""
    if not write_api:
        return
    try:
        point = Point(measurement)
        for k, v in fields.items():
            if isinstance(v, float):
                point = point.field(k, v)
            elif isinstance(v, (int, bool)):
                point = point.field(k, int(v))
            elif isinstance(v, str):
                point = point.field(k, v)
        if tags:
            for k, v in tags.items():
                point = point.tag(k, str(v))
        point = point.time(datetime.now(timezone.utc), WritePrecision.NS)
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    except Exception as e:
        print(f"[telemetry] InfluxDB write error: {e}")


def mavlink_loop():
    """Background thread: connect to MAVLink and update telemetry cache."""
    global telemetry_cache
    while True:
        try:
            conn = DroneConnection(udp_target=(MAVLINK_HOST, MAVLINK_PORT))
            conn.connect()
            print(f"[telemetry] MAVLink connected to {MAVLINK_HOST}:{MAVLINK_PORT}")
            while True:
                t = conn.get_telemetry()
                telemetry_cache["connected"] = t.get("connected", False)
                telemetry_cache["armed"] = t.get("armed", False)
                telemetry_cache["mode"] = t.get("mode", "UNKNOWN")
                telemetry_cache["lat"] = t.get("lat", 0.0)
                telemetry_cache["lon"] = t.get("lon", 0.0)
                telemetry_cache["alt"] = t.get("alt", 0.0)
                telemetry_cache["battery"] = t.get("battery", 0.0)
                telemetry_cache["heading"] = t.get("heading", 0.0)
                telemetry_cache["satellites"] = t.get("satellites", 0)
                telemetry_cache["fix_type"] = t.get("fix_type", 0)
                telemetry_cache["timestamp"] = datetime.now(timezone.utc).isoformat()

                # Write to InfluxDB
                if t.get("connected"):
                    gps_fields = {"latitude": t.get("lat", 0), "longitude": t.get("lon", 0),
                                  "altitude": t.get("alt", 0), "fix_type": t.get("fix_type", 0),
                                  "satellites": t.get("satellites", 0)}
                    write_to_influx("gps_telemetry", gps_fields, {"drone_id": "x500_0"})
                    metrics_count["gps_points"] += 1

                    batt_fields = {"battery_pct": t.get("battery", 0)}
                    write_to_influx("battery_telemetry", batt_fields, {"drone_id": "x500_0"})
                    metrics_count["battery_points"] += 1

                time.sleep(1)
        except Exception as e:
            print(f"[telemetry] MAVLink error: {e}, reconnecting in 3s...")
            telemetry_cache["connected"] = False
            time.sleep(3)


threading.Thread(target=mavlink_loop, daemon=True).start()
time.sleep(1)


# ── HTTP Server ──
class TelemetryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self._json(200, {"status": "ok", "service": "telemetry-collector",
                             "influxdb": INFLUX_AVAILABLE, "connected": telemetry_cache["connected"]})
        elif self.path == '/telemetry':
            self._json(200, telemetry_cache)
        elif self.path == '/metrics':
            self._json(200, {"telemetry": telemetry_cache, "counters": metrics_count})
        elif self.path == '/metrics/prometheus':
            t = telemetry_cache
            lines = [
                f'drone_connected {1 if t["connected"] else 0}',
                f'drone_armed {1 if t["armed"] else 0}',
                f'drone_altitude_m {t["alt"]}',
                f'drone_battery_pct {t["battery"]}',
                f'drone_heading_deg {t["heading"]}',
                f'drone_latitude {t["lat"]}',
                f'drone_longitude {t["lon"]}',
                f'drone_gps_satellites {t["satellites"]}',
                f'drone_gps_points_total {metrics_count["gps_points"]}',
                f'drone_battery_points_total {metrics_count["battery_points"]}',
            ]
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write('\n'.join(lines).encode())
        elif self.path == '/status':
            self._json(200, {
                "service": "telemetry-collector",
                "mavlink": {"host": MAVLINK_HOST, "port": MAVLINK_PORT},
                "influxdb": {"url": INFLUXDB_URL, "bucket": INFLUXDB_BUCKET, "available": INFLUX_AVAILABLE},
                "telemetry": telemetry_cache,
                "counters": metrics_count
            })
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == '/ingest':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                measurement = data.pop("measurement", "manual_telemetry")
                fields = {k: v for k, v in data.items() if isinstance(v, (int, float, str, bool))}
                tags = data.get("tags", {"source": "api"})
                write_to_influx(measurement, fields, tags)
                self._json(200, {"status": "written", "measurement": measurement})
            except Exception as e:
                self._json(400, {"error": str(e)})
        else:
            self._json(404, {"error": "not found"})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


server = HTTPServer(('0.0.0.0', PORT), TelemetryHandler)
print(f"[telemetry] Listening on :{PORT}/health, :{PORT}/telemetry, :{PORT}/metrics")
server.serve_forever()
