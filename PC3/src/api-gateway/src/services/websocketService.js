/**
 * WebSocket Service
 * Real-time telemetry broadcast to connected frontend clients.
 *
 * Protocol:
 *  - Client connects to ws://host:port
 *  - Server sends { type: 'welcome', data: {...} }
 *  - Client sends  { type: 'subscribe', topics: ['gps','battery'] }
 *  - Server pushes { type: 'telemetry', topic: 'gps', data: {...} }
 *  - Client sends  { type: 'ping' } → Server responds { type: 'pong' }
 */

'use strict';

const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');

let wss = null;

// Map of clientId → { ws, subscriptions: Set<string> }
const clients = new Map();

// ─── Init ─────────────────────────────────────────────────────────────────────
const initWebSocketServer = (httpServer) => {
  wss = new WebSocket.Server({ server: httpServer, path: '/ws' });

  wss.on('connection', (ws, req) => {
    const clientId = uuidv4();
    const ip = req.socket.remoteAddress;
    clients.set(clientId, { ws, subscriptions: new Set(['all']) });
    logger.info(`[WS] Client connected: ${clientId} from ${ip}. Total: ${clients.size}`);

    // Send welcome message
    send(ws, { type: 'welcome', clientId, timestamp: Date.now() });

    // Handle incoming messages from client
    ws.on('message', (raw) => handleClientMessage(clientId, ws, raw));

    // Handle disconnection
    ws.on('close', () => {
      clients.delete(clientId);
      logger.info(`[WS] Client disconnected: ${clientId}. Total: ${clients.size}`);
    });

    ws.on('error', (err) => {
      logger.error(`[WS] Client ${clientId} error: ${err.message}`);
      clients.delete(clientId);
    });
  });

  // Heartbeat ping every 30s to detect stale connections
  setInterval(() => {
    clients.forEach(({ ws }, clientId) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.ping();
      } else {
        clients.delete(clientId);
      }
    });
  }, parseInt(process.env.WS_PING_INTERVAL) || 30_000);

  logger.info('[WS] WebSocket server initialised at /ws');
  return wss;
};

// ─── Message handler ──────────────────────────────────────────────────────────
const handleClientMessage = (clientId, ws, raw) => {
  try {
    const msg = JSON.parse(raw.toString());

    switch (msg.type) {
      case 'ping':
        send(ws, { type: 'pong', timestamp: Date.now() });
        break;

      case 'subscribe': {
        const client = clients.get(clientId);
        if (client && Array.isArray(msg.topics)) {
          client.subscriptions = new Set(msg.topics);
          send(ws, { type: 'subscribed', topics: msg.topics, timestamp: Date.now() });
          logger.debug(`[WS] Client ${clientId} subscribed to: ${msg.topics.join(', ')}`);
        }
        break;
      }

      case 'unsubscribe': {
        const client = clients.get(clientId);
        if (client && Array.isArray(msg.topics)) {
          msg.topics.forEach((t) => client.subscriptions.delete(t));
          send(ws, { type: 'unsubscribed', topics: msg.topics, timestamp: Date.now() });
        }
        break;
      }

      default:
        send(ws, { type: 'error', message: `Unknown message type: ${msg.type}` });
    }
  } catch (err) {
    logger.error(`[WS] Parse error from client ${clientId}: ${err.message}`);
    send(ws, { type: 'error', message: 'Invalid JSON' });
  }
};

// ─── Broadcast helpers ────────────────────────────────────────────────────────

/** Send to a single WebSocket */
const send = (ws, payload) => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  }
};

/**
 * Broadcast telemetry to all subscribed clients.
 * @param {string} topic  - e.g. 'gps', 'battery', 'detections'
 * @param {object} data   - payload object
 */
const broadcast = (topic, data) => {
  if (!wss) return;

  const payload = JSON.stringify({ type: 'telemetry', topic, data, timestamp: Date.now() });

  clients.forEach(({ ws, subscriptions }, clientId) => {
    if (ws.readyState === WebSocket.OPEN) {
      // Send if client subscribed to 'all' OR the specific topic
      if (subscriptions.has('all') || subscriptions.has(topic)) {
        ws.send(payload);
      }
    } else {
      clients.delete(clientId);
    }
  });
};

/**
 * Broadcast a system alert to ALL connected clients regardless of subscription.
 */
const broadcastAlert = (alert) => {
  if (!wss) return;
  const payload = JSON.stringify({ type: 'alert', data: alert, timestamp: Date.now() });
  clients.forEach(({ ws }) => {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  });
};

/** Get live stats */
const getStats = () => ({
  connectedClients: clients.size,
  clientIds: [...clients.keys()],
});

module.exports = { initWebSocketServer, broadcast, broadcastAlert, getStats };
