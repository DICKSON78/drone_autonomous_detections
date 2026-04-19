/**
 * Alerts Routes
 *
 * GET  /api/alerts/active          - Currently active (within cooldown) alerts
 * POST /api/alerts/rules/reload    - Hot-reload alert rules from YAML
 * GET  /api/alerts/rules           - Get current rules in memory
 */

'use strict';

const express = require('express');
const { getActiveAlerts, reloadRules } = require('../services/alertService');

const router = express.Router();

router.get('/active', (req, res) => {
  const alerts = getActiveAlerts();
  res.json({ success: true, count: alerts.length, alerts });
});

router.post('/rules/reload', (req, res) => {
  reloadRules();
  res.json({ success: true, message: 'Alert rules reloaded from disk' });
});

module.exports = router;
