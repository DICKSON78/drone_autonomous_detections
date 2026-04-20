/**
 * Dashboard Routes
 *
 * GET /api/dashboard/summary?droneId=drone_001   - Combined overview (GPS + battery + flight + detections)
 * GET /api/dashboard/live?droneId=drone_001      - All latest readings in one call
 * GET /api/dashboard/websocket-stats             - How many WS clients are connected
 */

'use strict';

const express = require('express');
const telemetryService = require('../services/telemetryService');
const { getStats: wsStats } = require('../services/websocketService');
const { getActiveAlerts } = require('../services/alertService');

const router = express.Router();

// ─── Full summary (used by dashboard home page) ────────────────────────────────
router.get('/summary', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || req.query.drone_id || 'drone_001';
    const summary = await telemetryService.getDashboardSummary(droneId);
    res.json({ success: true, droneId, ...summary });
  } catch (err) { next(err); }
});

// ─── Live snapshot (all latest in parallel) ───────────────────────────────────
router.get('/live', async (req, res, next) => {
  try {
    const droneId = req.query.droneId || req.query.drone_id || 'drone_001';

    const [gps, battery, flight] = await Promise.allSettled([
      telemetryService.getLatestGps(droneId),
      telemetryService.getLatestBattery(droneId),
      telemetryService.getFlightStatus(droneId),
    ]);

    const alerts = getActiveAlerts();
    const ws     = wsStats();

    res.json({
      success: true,
      droneId,
      timestamp: new Date().toISOString(),
      live: {
        gps:     gps.status     === 'fulfilled' ? gps.value     : null,
        battery: battery.status === 'fulfilled' ? battery.value : null,
        flight:  flight.status  === 'fulfilled' ? flight.value  : null,
      },
      activeAlerts: alerts,
      websocket:    ws,
    });
  } catch (err) { next(err); }
});

// ─── WebSocket stats ──────────────────────────────────────────────────────────
router.get('/websocket-stats', (req, res) => {
  res.json({ success: true, ...wsStats(), timestamp: new Date().toISOString() });
});

module.exports = router;
