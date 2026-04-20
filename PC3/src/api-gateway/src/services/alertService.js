/**
 * Alert Service
 * Evaluates incoming telemetry against configurable rules.
 * Fires alerts via WebSocket when thresholds are breached.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const logger = require('../utils/logger');

// Dynamically require to avoid circular deps at load time
const getWs = () => require('./websocketService');

// ─── Load alert rules from YAML ───────────────────────────────────────────────
let RULES = {};

const loadRules = () => {
  try {
    const rulesPath = path.join(__dirname, '../../../../config/alert_rules.yaml');
    if (fs.existsSync(rulesPath)) {
      RULES = yaml.load(fs.readFileSync(rulesPath, 'utf8')) || {};
      logger.info('[Alerts] Rules loaded from alert_rules.yaml');
    } else {
      // Default built-in rules
      RULES = {
        battery: [
          { field: 'percentage', operator: '<', threshold: 20, severity: 'warning',  message: 'Battery low (< 20%)' },
          { field: 'percentage', operator: '<', threshold: 10, severity: 'critical', message: 'Battery critical (< 10%) - RTL recommended' },
        ],
        gps: [
          { field: 'altitude', operator: '>', threshold: 120, severity: 'warning', message: 'Altitude exceeds 120m limit' },
        ],
      };
      logger.info('[Alerts] Using default built-in rules');
    }
  } catch (err) {
    logger.error('[Alerts] Failed to load rules:', err.message);
  }
};

loadRules();

// ─── Active alert deduplication (suppress repeated same alerts) ───────────────
const _active = new Map(); // key → last fired timestamp
const COOLDOWN_MS = 30_000;

/**
 * Evaluate telemetry data against rules for a given topic.
 * @param {string} topic    - 'battery', 'gps', etc.
 * @param {object} data     - telemetry payload
 * @param {string} droneId
 */
const evaluate = async (topic, data, droneId) => {
  const rules = RULES[topic];
  if (!rules || !Array.isArray(rules)) return;

  for (const rule of rules) {
    const value = data[rule.field];
    if (value === undefined || value === null) continue;

    let triggered = false;
    switch (rule.operator) {
      case '<':  triggered = value < rule.threshold; break;
      case '>':  triggered = value > rule.threshold; break;
      case '<=': triggered = value <= rule.threshold; break;
      case '>=': triggered = value >= rule.threshold; break;
      case '==': triggered = value == rule.threshold; break;
      default:   break;
    }

    if (!triggered) continue;

    const alertKey = `${droneId}:${topic}:${rule.field}:${rule.threshold}`;
    const lastFired = _active.get(alertKey) || 0;
    if (Date.now() - lastFired < COOLDOWN_MS) continue; // still in cooldown

    _active.set(alertKey, Date.now());

    const alert = {
      id:        `${alertKey}:${Date.now()}`,
      drone_id:  droneId,
      topic,
      field:     rule.field,
      value,
      threshold: rule.threshold,
      operator:  rule.operator,
      severity:  rule.severity,
      message:   rule.message,
      timestamp: new Date().toISOString(),
    };

    logger.warn(`[Alert][${rule.severity.toUpperCase()}] ${alert.message} | value=${value}`);
    getWs().broadcastAlert(alert);
  }
};

/** Get all currently active alerts (within cooldown window) */
const getActiveAlerts = () => {
  const now = Date.now();
  return [..._active.entries()]
    .filter(([, ts]) => now - ts < COOLDOWN_MS)
    .map(([key, ts]) => ({ key, firedAt: new Date(ts).toISOString() }));
};

/** Reload rules from disk (useful for hot-reload) */
const reloadRules = () => loadRules();

module.exports = { evaluate, getActiveAlerts, reloadRules };
