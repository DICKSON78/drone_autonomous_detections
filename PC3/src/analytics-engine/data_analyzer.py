import os
import pandas as pd
from influxdb_client import InfluxDBClient
from datetime import datetime, timedelta
import json
import logging

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analytics-engine")

# ─── Config ───────────────────────────────────────────────────────────────────
INFLUX_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "drone-telemetry-token")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "drone-project")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "drone_telemetry")

class DataAnalyzer:
    def __init__(self):
        self.client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        self.query_api = self.client.query_api()

    def get_flight_summary(self, drone_id="drone_001", days=1):
        """Generates a flight performance summary for a given time range."""
        start_time = f"-{days}d"
        
        flux = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: {start_time})
          |> filter(fn: (r) => r._measurement == "gps_telemetry" and r.drone_id == "{drone_id}")
          |> filter(fn: (r) => r._field == "altitude" or r._field == "speed")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        try:
            df = self.query_api.query_data_frame(flux)
            if df.empty:
                return {"status": "no_data", "message": "No telemetry found for the period."}
            
            summary = {
                "drone_id": drone_id,
                "period_days": days,
                "max_altitude": float(df["altitude"].max()),
                "avg_altitude": float(df["altitude"].mean()),
                "max_speed": float(df["speed"].max()),
                "avg_speed": float(df["speed"].mean()),
                "total_readings": len(df),
                "timestamp": datetime.now().isoformat()
            }
            return summary
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")
            return {"status": "error", "message": str(e)}

    def get_battery_efficiency(self, drone_id="drone_001"):
        """Analyzes battery drain relative to flight time."""
        flux = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "battery_telemetry" and r.drone_id == "{drone_id}")
          |> filter(fn: (r) => r._field == "percentage")
          |> sort(columns: ["_time"])
        '''
        
        try:
            df = self.query_api.query_data_frame(flux)
            if len(df) < 2:
                return {"status": "insufficient_data"}
            
            drain = df["_value"].iloc[0] - df["_value"].iloc[-1]
            time_diff = (df["_time"].iloc[-1] - df["_time"].iloc[0]).total_seconds() / 60.0 # in minutes
            
            return {
                "drone_id": drone_id,
                "drain_percentage": float(drain),
                "flight_duration_min": float(time_diff),
                "drain_rate_per_min": float(drain / time_diff) if time_diff > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error analyzing battery: {e}")
            return {"status": "error", "message": str(e)}

    def generate_daily_report(self, output_path="./reports"):
        """Generates a comprehensive JSON report for all drones."""
        os.makedirs(output_path, exist_ok=True)
        
        # In a real scenario, we'd find all unique drone IDs
        drone_ids = ["drone_001"] 
        
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "drones": []
        }
        
        for d_id in drone_ids:
            summary = self.get_flight_summary(d_id)
            battery = self.get_battery_efficiency(d_id)
            report["drones"].append({
                "drone_id": d_id,
                "flight_summary": summary,
                "battery_analysis": battery
            })
            
        filename = f"report_{report['date']}.json"
        with open(os.path.join(output_path, filename), "w") as f:
            json.dump(report, f, indent=4)
            
        logger.info(f"Daily report generated: {filename}")
        return report

if __name__ == "__main__":
    analyzer = DataAnalyzer()
    print(json.dumps(analyzer.get_flight_summary(), indent=2))
