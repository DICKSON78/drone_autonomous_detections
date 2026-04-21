const WebSocket = require('ws');
const http = require('http');
const express = require('express');
const cors = require('cors');
const kafkaListener = require('./kafka_listener');
const messageHandler = require('./message_handler');
const clientManager = require('./client_manager');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = process.env.WS_PORT || 8006;

// ── WebSocket connections ──────────────────────────────────────────────────

wss.on('connection', (ws, req) => {
  const clientId = clientManager.addClient(ws, req);
  console.log(`[WS] Client connected: ${clientId}`);

  ws.on('message', (rawMsg) => {
    try {
      const msg = JSON.parse(rawMsg);
      messageHandler.handleClientMessage(msg, clientId, clientManager);
    } catch (e) {
      console.error(`[WS] Invalid message from ${clientId}:`, e.message);
    }
  });

  ws.on('close', () => {
    clientManager.removeClient(clientId);
    console.log(`[WS] Client disconnected: ${clientId}`);
  });

  ws.on('error', (err) => {
    console.error(`[WS] Error from ${clientId}:`, err.message);
    clientManager.removeClient(clientId);
  });

  // Send initial state on connect
  ws.send(JSON.stringify({
    type: 'connected',
    clientId,
    timestamp: Date.now()
  }));
});

// ── REST health endpoints ──────────────────────────────────────────────────

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'websocket-server',
    clients: clientManager.count(),
    timestamp: Date.now()
  });
});

app.get('/clients', (req, res) => {
  res.json({ clients: clientManager.list() });
});

app.post('/broadcast', (req, res) => {
  const { type, data } = req.body;
  if (!type) return res.status(400).json({ error: 'type field required' });
  const sent = clientManager.broadcast({ type, data, timestamp: Date.now() });
  res.json({ status: 'broadcast', recipients: sent });
});

// ── Start ──────────────────────────────────────────────────────────────────

server.listen(PORT, () => {
  console.log(`[WS] WebSocket server listening on port ${PORT}`);
  kafkaListener.start(clientManager, messageHandler);
});

module.exports = { wss, server };