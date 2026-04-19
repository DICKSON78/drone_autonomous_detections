/**
 * Telemetry Service
 * Flux query builders for all telemetry measurements stored in InfluxDB
 */

'use strict';

const { query, INFLUX_BUCKET } = require('../config/influxdb');
const logger = require('../utils/logger');

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Map user-friendly window strings to InfluxDB range format */
const parseRange = (range = '1h') => {
  const allowed = ['5m','10m','30m','1h','3h','6h','12h','24h','7d','30d'];
  return allowed.includes(range) ? `-${range}` : '-1h';
};

/** Build a base Flux query filtered by droneId if provided */
const baseQuery = (measurement, range, droneId) => {
  let q = `
    from(bucket: "${INFLUX_BUCKET}")
      |> range(start: ${parseRange(range)})
      |> filter(fn: (r) => r._measurement == "${measurement}")
  `;
  if (droneId) {
    q += `  |> filter(fn: (r) => r.drone_id == "${droneId}")\n`;
  }
  return q;
};

// ─── GPS ──────────────────────────────────────────────────────────────────────
const getGpsHistory = async ({ droneId, range = '1h', limit = 500 } = {}) => {
  const flux = baseQuery('gps_telemetry', range, droneId) + `
    |> filter(fn: (r) => r._field == "latitude" or r._field == "longitude" or r._field == "altitude" or r._field == "speed")
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> sort(columns: ["_time"])
    |> limit(n: ${Math.min(limit, 1000)})
  `;
  return query(flux);
};

const getLatestGps = async (droneId) => {
  const flux = baseQuery('gps_telemetry', '5m', droneId) + `
    |> filter(fn: (r) => r._field == "latitude" or r._field == "longitude" or r._field == "altitude" or r._field == "speed")
    |> last()
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  `;
  const rows = await query(flux);
  return rows.length ? rows[rows.length - 1] : null;
};

// ─── Battery ──────────────────────────────────────────────────────────────────
const getBatteryHistory = async ({ droneId, range = '1h' } = {}) => {
  const flux = baseQuery('battery_telemetry', range, droneId) + `
    |> filter(fn: (r) => r._field == "percentage" or r._field == "voltage" or r._field == "current" or r._field == "temperature")
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> sort(columns: ["_time"])
  `;
  return query(flux);
};

const getLatestBattery = async (droneId) => {
  const flux = baseQuery('battery_telemetry', '5m', droneId) + `
    |> filter(fn: (r) => r._field == "percentage" or r._field == "voltage")
    |> last()
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  `;
  const rows = await query(flux);
  return rows.length ? rows[rows.length - 1] : null;
};

// ─── Attitude ─────────────────────────────────────────────────────────────────
const getAttitudeHistory = async ({ droneId, range = '1h' } = {}) => {
  const flux = baseQuery('attitude_telemetry', range, droneId) + `
    |> filter(fn: (r) => r._field == "roll_deg" or r._field == "pitch_deg" or r._field == "yaw_deg")
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> sort(columns: ["_time"])
  `;
  return query(flux);
};

// ─── Flight Status ────────────────────────────────────────────────────────────
const getFlightStatus = async (droneId) => {
  const flux = baseQuery('flight_status', '5m', droneId) + `
    |> filter(fn: (r) => r._field == "altitude_m" or r._field == "speed_ms")
    |> last()
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  `;
  const rows = await query(flux);
  return rows.length ? rows[rows.length - 1] : null;
};

// ─── Object Detections ────────────────────────────────────────────────────────
const getDetections = async ({ droneId, range = '1h', objectClass } = {}) => {
  let flux = baseQuery('object_detections', range, droneId) + `
    |> filter(fn: (r) => r._field == "confidence")
  `;
  if (objectClass) {
    flux += `  |> filter(fn: (r) => r.object_class == "${objectClass}")\n`;
  }
  flux += `
    |> pivot(rowKey: ["_time", "object_class"], columnKey: ["_field"], valueColumn: "_value")
    |> sort(columns: ["_time"], desc: true)
  `;
  return query(flux);
};

const getDetectionSummary = async ({ droneId, range = '1h' } = {}) => {
  const flux = baseQuery('object_detections', range, droneId) + `
    |> filter(fn: (r) => r._field == "confidence")
    |> group(columns: ["object_class"])
    |> count()
    |> rename(columns: {_value: "count"})
  `;
  return query(flux);
};

// ─── Navigation ───────────────────────────────────────────────────────────────
const getNavigationHistory = async ({ droneId, range = '1h' } = {}) => {
  const flux = baseQuery('navigation_telemetry', range, droneId) + `
    |> filter(fn: (r) => r._field == "confidence" or r._field == "estimated_time" or r._field == "path_length")
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> sort(columns: ["_time"])
  `;
  return query(flux);
};

// ─── Summary / Dashboard Overview ─────────────────────────────────────────────
const getDashboardSummary = async (droneId) => {
  const [gps, battery, flight, detectSummary] = await Promise.allSettled([
    getLatestGps(droneId),
    getLatestBattery(droneId),
    getFlightStatus(droneId),
    getDetectionSummary({ droneId, range: '1h' }),
  ]);

  return {
    gps:              gps.status === 'fulfilled'    ? gps.value          : null,
    battery:          battery.status === 'fulfilled' ? battery.value      : null,
    flight:           flight.status === 'fulfilled'  ? flight.value       : null,
    detectionSummary: detectSummary.status === 'fulfilled' ? detectSummary.value : [],
    timestamp:        new Date().toISOString(),
  };
};

module.exports = {
  getGpsHistory,
  getLatestGps,
  getBatteryHistory,
  getLatestBattery,
  getAttitudeHistory,
  getFlightStatus,
  getDetections,
  getDetectionSummary,
  getNavigationHistory,
  getDashboardSummary,
};
