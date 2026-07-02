import os
import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Optional


DB_PATH = os.environ.get("TELEMETRY_DB_PATH", "telemetry.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            armed INTEGER,
            in_air INTEGER,
            altitude REAL,
            heading REAL,
            speed REAL,
            battery REAL,
            lat REAL,
            lon REAL,
            vx REAL,
            vy_real REAL,
            vz REAL,
            climb REAL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry(ts)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            class_name TEXT,
            distance REAL,
            bearing_h REAL,
            confidence REAL
        )
    """)
    conn.commit()
    conn.close()


def insert_telemetry(state: dict):
    conn = _get_conn()
    conn.execute("""
        INSERT INTO telemetry (ts, armed, in_air, altitude, heading, speed, battery, lat, lon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        time.time(),
        1 if state.get("armed") else 0,
        1 if state.get("in_air") else 0,
        state.get("altitude", 0),
        state.get("heading", 0),
        state.get("speed", 0),
        state.get("battery", 100),
        state.get("lat", 0),
        state.get("lon", 0),
    ))
    conn.commit()
    conn.close()


def insert_event(event_type: str, message: str):
    conn = _get_conn()
    conn.execute("INSERT INTO events (ts, event_type, message) VALUES (?, ?, ?)",
                 (time.time(), event_type, message))
    conn.commit()
    conn.close()


def get_telemetry_history(hours: float = 1) -> list:
    conn = _get_conn()
    since = time.time() - hours * 3600
    rows = conn.execute(
        "SELECT * FROM telemetry WHERE ts >= ? ORDER BY ts ASC", (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_events(limit: int = 100) -> list:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_telemetry() -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM telemetry ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_detection(det: dict):
    conn = _get_conn()
    conn.execute("""
        INSERT INTO detections (ts, class_name, distance, bearing_h, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (
        time.time(),
        det.get("class_name", "unknown"),
        det.get("distance", 0),
        det.get("bearing_h", 0),
        det.get("confidence", 0),
    ))
    conn.commit()
    conn.close()


def cleanup_old(hours: float = 48):
    conn = _get_conn()
    since = time.time() - hours * 3600
    conn.execute("DELETE FROM telemetry WHERE ts < ?", (since,))
    conn.execute("DELETE FROM events WHERE ts < ?", (since,))
    conn.execute("DELETE FROM detections WHERE ts < ?", (since,))
    conn.commit()
    conn.close()


# ── Init on import ──
init_db()
