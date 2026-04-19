/**
 * GET /api/health
 * GET /api/health/detailed
 *
 * Reports liveness and readiness of all PC3 sub-systems:
 *  - InfluxDB
 *  - Kafka
 *  - Python Telemetry Collector (port 8004)
 *  - Grafana
 *  - WebSocket server
 */

'use strict';

const express = require('express');
const axios   = require('axios');
const { checkHealth: influxHealth } = require('../config/influxdb');
const { kafka }                     = require('../config/kafka');
const { getStats: wsStats }         = require('../services/websocketService');
const logger = require('../utils/logger');

const router = express.Router();

// ─── Simple ping ──────────────────────────────────────────────────────────────
router.get('/', (req, res) => {
  res.json({ status: 'ok', service: 'pc3-api-gateway', timestamp: new Date().toISOString() });
});

// ─── Detailed check ───────────────────────────────────────────────────────────
router.get('/detailed', async (req, res, next) => {
  try {
    const checks = await Promise.allSettled([
      influxHealth(),
      checkKafka(),
      checkTelemetryCollector(),
      checkGrafana(),
    ]);

    const [influx, kafka, telemetry, grafana] = checks.map((r) =>
      r.status === 'fulfilled' ? r.value : { connected: false, error: r.reason?.message }
    );

    const ws = wsStats();
    const allHealthy = influx.connected && kafka.connected;

    res.status(allHealthy ? 200 : 503).json({
      status:    allHealthy ? 'healthy' : 'degraded',
      service:   'pc3-api-gateway',
      timestamp: new Date().toISOString(),
      checks: {
        influxdb:            influx,
        kafka:               kafka,
        telemetry_collector: telemetry,
        grafana:             grafana,
        websocket: {
          connected:        true,
          clients:          ws.connectedClients,
        },
      },
    });
  } catch (err) {
    next(err);
  }
});

// ─── Sub-system checkers ──────────────────────────────────────────────────────
const checkKafka = async () => {
  const admin = kafka.admin();
  try {
    await admin.connect();
    const topics = await admin.listTopics();
    await admin.disconnect();
    return { connected: true, topics };
  } catch (err) {
    return { connected: false, error: err.message };
  }
};

const checkTelemetryCollector = async () => {
  try {
    const url = process.env.TELEMETRY_COLLECTOR_URL || 'http://localhost:8004';
    const res = await axios.get(`${url}/health`, { timeout: 3000 });
    return { connected: true, status: res.data?.status, url };
  } catch (err) {
    return { connected: false, error: err.message, url: process.env.TELEMETRY_COLLECTOR_URL };
  }
};

const checkGrafana = async () => {
  try {
    const url = process.env.GRAFANA_URL || 'http://localhost:3000';
    const res = await axios.get(`${url}/api/health`, { timeout: 3000 });
    return { connected: true, version: res.data?.version, url };
  } catch (err) {
    return { connected: false, error: err.message };
  }
};

module.exports = router;
