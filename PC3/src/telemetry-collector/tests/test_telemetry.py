"""
Integration tests for PC3 Telemetry Collector
Tests: data processors, InfluxDB writes, API endpoints, Kafka mock
"""

import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# ─── Mock InfluxDB before import ──────────────────────────────────────────────
mock_write_api = MagicMock()
mock_influx    = MagicMock()
mock_influx.health.return_value = MagicMock(status="pass")

with patch("influxdb_client.InfluxDBClient", return_value=mock_influx):
    mock_influx.write_api.return_value = mock_write_api
    from telemetry import (
        process_gps, process_battery, process_attitude,
        process_flight, process_detections, process_navigation,
        process_system, app,
    )

from fastapi.testclient import TestClient

client = TestClient(app)


# ─── Processor Tests ──────────────────────────────────────────────────────────
class TestProcessors(unittest.TestCase):

    def setUp(self):
        mock_write_api.reset_mock()

    def _get_written_point(self):
        """Extract the first Point written to InfluxDB"""
        self.assertTrue(mock_write_api.write.called, "Expected InfluxDB write to be called")
        call_kwargs = mock_write_api.write.call_args
        return call_kwargs

    def test_process_gps_standard(self):
        """GPS data with standard field names"""
        data = {"drone_id": "drone_001", "latitude": -1.2921, "longitude": 36.8219, "altitude": 50.0, "speed": 5.0}
        process_gps(data)
        self.assertTrue(mock_write_api.write.called)

    def test_process_gps_mavsdk_names(self):
        """GPS data with MAVSDK field names (lat/lon/alt)"""
        data = {"drone_id": "drone_001", "lat": -1.2921, "lon": 36.8219, "alt": 50.0}
        process_gps(data)
        self.assertTrue(mock_write_api.write.called)

    def test_process_battery_full(self):
        data = {
            "drone_id": "drone_001",
            "percentage": 85.0,
            "voltage_v": 15.8,
            "current_battery": 12.3,
            "temperature_degc": 28.0,
        }
        process_battery(data)
        self.assertTrue(mock_write_api.write.called)

    def test_process_battery_simple(self):
        """Fallback to simpler field names"""
        data = {"drone_id": "drone_001", "percentage": 55.0, "voltage": 14.8}
        process_battery(data)
        self.assertTrue(mock_write_api.write.called)

    def test_process_attitude(self):
        data = {"drone_id": "drone_001", "roll_deg": 5.0, "pitch_deg": -3.2, "yaw_deg": 120.0}
        process_attitude(data)
        self.assertTrue(mock_write_api.write.called)

    def test_process_flight_status(self):
        data = {"drone_id": "drone_001", "is_armed": True, "is_flying": True, "flight_mode": "MISSION", "altitude": 45.0, "speed": 8.0}
        process_flight(data)
        self.assertTrue(mock_write_api.write.called)

    def test_process_detections_multiple(self):
        data = {
            "drone_id": "drone_001",
            "detections": [
                {"class_name": "tree",   "confidence": 0.92, "bbox": [100, 200, 50, 80]},
                {"class_name": "animal", "confidence": 0.78, "bbox": [300, 400, 60, 90]},
            ],
        }
        process_detections(data)
        # Should write 2 points
        self.assertEqual(mock_write_api.write.call_count, 2)

    def test_process_detections_empty(self):
        data = {"drone_id": "drone_001", "detections": []}
        process_detections(data)
        self.assertFalse(mock_write_api.write.called)

    def test_process_navigation(self):
        data = {
            "drone_id": "drone_001",
            "next_action": "avoid_left",
            "confidence": 0.88,
            "estimated_time": 3.5,
            "path": [[1, 2], [3, 4], [5, 6]],
        }
        process_navigation(data)
        self.assertTrue(mock_write_api.write.called)


# ─── API Endpoint Tests ────────────────────────────────────────────────────────
class TestAPIEndpoints(unittest.TestCase):

    def test_health_endpoint(self):
        resp = client.get("/health")
        self.assertIn(resp.status_code, [200, 503])
        body = resp.json()
        self.assertIn("status",  body)
        self.assertIn("service", body)
        self.assertEqual(body["service"], "telemetry-collector")

    def test_status_endpoint(self):
        resp = client.get("/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("service",  body)
        self.assertIn("stats",    body)
        self.assertIn("influxdb", body)

    def test_metrics_endpoint(self):
        resp = client.get("/metrics")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("messages_processed_total", body)
        self.assertIn("active_consumers",         body)

    def test_telemetry_ingest_gps(self):
        resp = client.post("/telemetry", json={
            "drone_id":  "drone_001",
            "data_type": "gps",
            "data":      {"latitude": -1.29, "longitude": 36.82, "altitude": 50, "speed": 5},
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    def test_telemetry_ingest_battery(self):
        resp = client.post("/telemetry", json={
            "drone_id":  "drone_001",
            "data_type": "battery",
            "data":      {"percentage": 75.0, "voltage": 15.5},
        })
        self.assertEqual(resp.status_code, 200)

    def test_telemetry_ingest_invalid_type(self):
        resp = client.post("/telemetry", json={
            "drone_id":  "drone_001",
            "data_type": "invalid_type",
            "data":      {"foo": "bar"},
        })
        self.assertIn(resp.status_code, [400, 422])

    def test_telemetry_ingest_missing_fields(self):
        resp = client.post("/telemetry", json={"data_type": "gps"})
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
