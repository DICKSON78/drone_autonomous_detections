/**
 * Telemetry Routes
 *
 * GET  /api/telemetry/gps?range=1h&droneId=drone_001&limit=500
 * GET  /api/telemetry/gps/latest?droneId=drone_001
 * GET  /api/telemetry/battery?range=1h&droneId=drone_001
 * GET  /api/telemetry/battery/latest?droneId=drone_001
 * GET  /api/telemetry/attitude?range=1h&droneId=drone_001
 * GET  /api/telemetry/flight?droneId=drone_001
 * GET  /api/telemetry/detections?range=1h&droneId=drone_001&class=tree
 * GET  /api/telemetry/detections/summary?range=1h&droneId=drone_001
 * GET  /api/telemetry/navigation?range=1h&droneId=drone_001
 * POST /api/telemetry         (receive telemetry via REST, write to InfluxDB)
 */

'use strict';

const express = require('express');
const { body, query, validationResult } = require('express-validator');
const telemetryService = require('../services/telemetryService');
const { writePoint, Point } = require('../config/influxdb');
const { broadcast } = require('../services/websocketService');
const logger = require('../utils/logger');

const router = express.Router();

// ─── Common query extractor ────────────────────────────────────────────────────
const extractQuery = (req) => ({
  droneId: req.query.droneId || req.query.drone_id || null,
  range:   req.query.range   || '1h',
  limit:   parseInt(req.query.limit)  || 500,
});

// ─── GPS ──────────────────────────────────────────────────────────────────────
router.get('/gps', async (req, res, next) => {
  try {
    const { droneId, range, limit } = extractQuery(req);
    const data = await telemetryService.getGpsHistory({ droneId, range, limit });
    res.json({ success: true, count: data.length, range, droneId, data });
  } catch (err) { next(err); }
});

router.get('/gps/latest', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || req.query.drone_id;
    const data = await telemetryService.getLatestGps(droneId);
    if (!data) return res.status(404).json({ error: 'No GPS data found' });
    res.json({ success: true, droneId, data });
  } catch (err) { next(err); }
});

// ─── Battery ──────────────────────────────────────────────────────────────────
router.get('/battery', async (req, res, next) => {
  try {
    const { droneId, range } = extractQuery(req);
    const data = await telemetryService.getBatteryHistory({ droneId, range });
    res.json({ success: true, count: data.length, range, droneId, data });
  } catch (err) { next(err); }
});

router.get('/battery/latest', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || req.query.drone_id;
    const data = await telemetryService.getLatestBattery(droneId);
    if (!data) return res.status(404).json({ error: 'No battery data found' });
    res.json({ success: true, droneId, data });
  } catch (err) { next(err); }
});

// ─── Attitude ─────────────────────────────────────────────────────────────────
router.get('/attitude', async (req, res, next) => {
  try {
    const { droneId, range } = extractQuery(req);
    const data = await telemetryService.getAttitudeHistory({ droneId, range });
    res.json({ success: true, count: data.length, range, droneId, data });
  } catch (err) { next(err); }
});

// ─── Flight Status ────────────────────────────────────────────────────────────
router.get('/flight', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || req.query.drone_id;
    const data = await telemetryService.getFlightStatus(droneId);
    if (!data) return res.status(404).json({ error: 'No flight data found' });
    res.json({ success: true, droneId, data });
  } catch (err) { next(err); }
});

// ─── Detections ───────────────────────────────────────────────────────────────
router.get('/detections', async (req, res, next) => {
  try {
    const { droneId, range, limit } = extractQuery(req);
    const objectClass = req.query.class || req.query.objectClass || null;
    const data = await telemetryService.getDetections({ droneId, range, objectClass });
    res.json({ success: true, count: data.length, range, droneId, objectClass, data });
  } catch (err) { next(err); }
});

router.get('/detections/summary', async (req, res, next) => {
  try {
    const { droneId, range } = extractQuery(req);
    const data = await telemetryService.getDetectionSummary({ droneId, range });
    res.json({ success: true, range, droneId, data });
  } catch (err) { next(err); }
});

// ─── Navigation ───────────────────────────────────────────────────────────────
router.get('/navigation', async (req, res, next) => {
  try {
    const { droneId, range } = extractQuery(req);
    const data = await telemetryService.getNavigationHistory({ droneId, range });
    res.json({ success: true, count: data.length, range, droneId, data });
  } catch (err) { next(err); }
});

// ─── Ingest via REST (Python services can push here too) ──────────────────────
router.post(
  '/',
  [
    body('drone_id').notEmpty().withMessage('drone_id is required'),
    body('data_type').isIn(['gps', 'battery', 'attitude', 'flight', 'detections', 'navigation', 'system'])
      .withMessage('Invalid data_type'),
    body('data').isObject().withMessage('data must be an object'),
  ],
  async (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    try {
      const { drone_id, data_type, data } = req.body;
      const merged = { drone_id, ...data };

      // Write generic point to InfluxDB
      const point = new Point(`${data_type}_telemetry`)
        .tag('drone_id', drone_id)
        .tag('source', 'rest-api')
        .timestamp(new Date());

      Object.entries(data).forEach(([k, v]) => {
        if (typeof v === 'number') point.floatField(k, v);
        else if (typeof v === 'boolean') point.booleanField(k, v);
        else if (typeof v === 'string') point.stringField(k, v);
      });

      await writePoint(point);

      // Also broadcast over WebSocket
      broadcast(data_type, merged);

      logger.info(`[REST Ingest] drone=${drone_id} type=${data_type}`);
      res.status(201).json({ success: true, message: 'Telemetry ingested', drone_id, data_type });
    } catch (err) {
      next(err);
    }
  }
);

module.exports = router;
