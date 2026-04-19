import requests
import json
import os
import logging

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dashboard-builder")

# ─── Config ───────────────────────────────────────────────────────────────────
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASS = os.getenv("GRAFANA_PASS", "admin123")

class DashboardBuilder:
    def __init__(self):
        self.base_url = GRAFANA_URL.rstrip("/")
        self.auth = (GRAFANA_USER, GRAFANA_PASS)

    def check_connection(self):
        """Verifies connection to Grafana API."""
        try:
            response = requests.get(f"{self.base_url}/api/health", auth=self.auth, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def create_or_update_dashboard(self, dashboard_json_path):
        """Uploads a dashboard JSON to Grafana."""
        if not os.path.exists(dashboard_json_path):
            logger.error(f"Dashboard file not found: {dashboard_json_path}")
            return False

        with open(dashboard_json_path, "r") as f:
            dashboard_data = json.load(f)

        # Structure for Grafana API: {"dashboard": ..., "overwrite": true}
        payload = {
            "dashboard": dashboard_data,
            "overwrite": True
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/dashboards/db",
                json=payload,
                auth=self.auth,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Dashboard successfully uploaded: {dashboard_data.get('title')}")
                return True
            else:
                logger.error(f"Failed to upload dashboard: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error communicating with Grafana: {e}")
            return False

    def create_datasource(self, name, ds_type, url, token, org, bucket):
        """Programmatically adds an InfluxDB datasource."""
        payload = {
            "name": name,
            "type": ds_type,
            "url": url,
            "access": "proxy",
            "basicAuth": False,
            "jsonData": {
                "organization": org,
                "defaultBucket": bucket,
                "version": "Flux",
                "httpMode": "POST"
            },
            "secureJsonData": {
                "token": token
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/datasources",
                json=payload,
                auth=self.auth
            )
            if response.status_code in [200, 409]: # 409 if exists
                logger.info(f"Datasource ensured: {name}")
                return True
            else:
                logger.error(f"Failed to create datasource: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating datasource: {e}")
            return False

if __name__ == "__main__":
    builder = DashboardBuilder()
    if builder.check_connection():
        # Example usage
        builder.create_datasource(
            "InfluxDB-Drone", "influxdb", 
            "http://influxdb:8086", "drone-telemetry-token", "drone-project", "drone_telemetry"
        )
        # builder.create_or_update_dashboard("./dashboards/master-dashboard.json")
    else:
        logger.warning("Grafana API not reachable. Check if service is running.")
