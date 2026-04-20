/**
 * Analytics Routes
 *
 * GET /api/analytics/flight-stats?droneId=drone_001&range=24h
 * GET /api/analytics/detection-trends?range=24h&droneId=drone_001
 * GET /api/analytics/battery-health?droneId=drone_001&range=24h
 * GET /api/analytics/path?droneId=drone_001&range=1h
 */

'use strict';

const express = require('express');
const { query: influxQuery, INFLUX_BUCKET } = require('../config/influxdb');

const router = express.Router();

const parseRange = (r = '24h') => {
  const allowed = ['30m','1h','3h','6h','12h','24h','7d','30d'];
  return allowed.includes(r) ? `-${r}` : '-24h';
};

// ─── Flight statistics ────────────────────────────────────────────────────────
router.get('/flight-stats', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || 'drone_001';
    const range   = parseRange(req.query.range);

    const [altStats, speedStats, gpsCount] = await Promise.all([
      influxQuery(`
        from(bucket: "${INFLUX_BUCKET}")
          |> range(start: ${range})
          |> filter(fn: (r) => r._measurement == "gps_telemetry" and r._field == "altitude" and r.drone_id == "${droneId}")
          |> mean()
      `),
      influxQuery(`
        from(bucket: "${INFLUX_BUCKET}")
          |> range(start: ${range})
          |> filter(fn: (r) => r._measurement == "gps_telemetry" and r._field == "speed" and r.drone_id == "${droneId}")
          |> mean()
      `),
      influxQuery(`
        from(bucket: "${INFLUX_BUCKET}")
          |> range(start: ${range})
          |> filter(fn: (r) => r._measurement == "gps_telemetry" and r._field == "latitude" and r.drone_id == "${droneId}")
          |> count()
      `),
    ]);

    res.json({
      success: true,
      droneId,
      range: req.query.range || '24h',
      stats: {
        avg_altitude_m: altStats[0]?._value ?? null,
        avg_speed_ms:   speedStats[0]?._value ?? null,
        total_readings: gpsCount[0]?._value ?? 0,
      },
    });
  } catch (err) { next(err); }
});

// ─── Detection trends ─────────────────────────────────────────────────────────
router.get('/detection-trends', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || 'drone_001';
    const range   = parseRange(req.query.range);

    const rows = await influxQuery(`
      from(bucket: "${INFLUX_BUCKET}")
        |> range(start: ${range})
        |> filter(fn: (r) => r._measurement == "object_detections" and r._field == "confidence" and r.drone_id == "${droneId}")
        |> group(columns: ["object_class"])
        |> count()
        |> rename(columns: {_value: "count"})
    `);

    const trends = rows.map((r) => ({
      object_class: r.object_class,
      count:        r.count ?? r._value,
    }));

    res.json({ success: true, droneId, range: req.query.range || '24h', trends });
  } catch (err) { next(err); }
});

// ─── Battery health ───────────────────────────────────────────────────────────
router.get('/battery-health', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || 'drone_001';
    const range   = parseRange(req.query.range);

    const [minBat, avgBat, maxVolt] = await Promise.all([
      influxQuery(`
        from(bucket: "${INFLUX_BUCKET}")
          |> range(start: ${range})
          |> filter(fn: (r) => r._measurement == "battery_telemetry" and r._field == "percentage" and r.drone_id == "${droneId}")
          |> min()
      `),
      influxQuery(`
        from(bucket: "${INFLUX_BUCKET}")
          |> range(start: ${range})
          |> filter(fn: (r) => r._measurement == "battery_telemetry" and r._field == "percentage" and r.drone_id == "${droneId}")
          |> mean()
      `),
      influxQuery(`
        from(bucket: "${INFLUX_BUCKET}")
          |> range(start: ${range})
          |> filter(fn: (r) => r._measurement == "battery_telemetry" and r._field == "voltage" and r.drone_id == "${droneId}")
          |> max()
      `),
    ]);

    res.json({
      success: true,
      droneId,
      range: req.query.range || '24h',
      battery: {
        min_percentage: minBat[0]?._value ?? null,
        avg_percentage: avgBat[0]?._value ?? null,
        max_voltage:    maxVolt[0]?._value ?? null,
        health_status:
          (minBat[0]?._value ?? 100) < 10 ? 'critical' :
          (minBat[0]?._value ?? 100) < 25 ? 'warning' : 'good',
      },
    });
  } catch (err) { next(err); }
});

// ─── GPS flight path ──────────────────────────────────────────────────────────
router.get('/path', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || 'drone_001';
    const range   = parseRange(req.query.range || '1h');
    const limit   = Math.min(parseInt(req.query.limit) || 1000, 5000);

    const rows = await influxQuery(`
      from(bucket: "${INFLUX_BUCKET}")
        |> range(start: ${range})
        |> filter(fn: (r) => r._measurement == "gps_telemetry" and r.drone_id == "${droneId}")
        |> filter(fn: (r) => r._field == "latitude" or r._field == "longitude" or r._field == "altitude")
        |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"])
        |> limit(n: ${limit})
    `);

    const path = rows.map((r) => ({
      time:      r._time,
      latitude:  r.latitude,
      longitude: r.longitude,
      altitude:  r.altitude,
    }));

    res.json({ success: true, droneId, range: req.query.range || '1h', count: path.length, path });
  } catch (err) { next(err); }
});

module.exports = router;
