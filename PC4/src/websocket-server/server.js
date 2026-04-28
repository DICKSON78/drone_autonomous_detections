/**
 * server.js — PC4 WebSocket Server
 * Serves:
 *   • WebSocket endpoint  ws://host:8006
 *   • REST API            http://host:8006/{health,clients,broadcast}
 */

const http    = require("http");
const express = require("express");
const cors    = require("cors");
const { WebSocketServer } = require("ws");

const { ClientManager }    = require("./client_manager");
const { handleClientMessage } = require("./message_handler");
const { startKafkaListener }  = require("./kafka_listener");

const WS_PORT = parseInt(process.env.WS_PORT || "8006", 10);

// ── Express app ───────────────────────────────────────────────────────────────

const app = express();
app.use(cors());
app.use(express.json());

const server  = http.createServer(app);
const wss     = new WebSocketServer({ server });
const clients = new ClientManager();

// ── WebSocket ─────────────────────────────────────────────────────────────────

wss.on("connection", (ws, req) => {
  const id = clients.add(ws, req);

  // Send welcome message
  clients.send(id, { type: "connected", clientId: id, timestamp: Date.now() });

  ws.on("message", (raw) => {
    const { reply, broadcast } = handleClientMessage(raw.toString(), id, clients);
    if (reply)     clients.send(id, reply);
    if (broadcast) clients.broadcast(broadcast);
  });

  ws.on("close", () => clients.remove(id));

  ws.on("error", (err) => {
    console.error(`[ws] client ${id} error:`, err.message);
    clients.remove(id);
  });
});

// ── REST endpoints ────────────────────────────────────────────────────────────

app.get("/health", (_req, res) => {
  res.json({
    status:    "healthy",
    service:   "websocket-server",
    clients:   clients.size,
    timestamp: Date.now(),
  });
});

app.get("/clients", (_req, res) => {
  res.json({ clients: clients.list() });
});

app.post("/broadcast", (req, res) => {
  const { type, data } = req.body ?? {};
  if (!type) return res.status(400).json({ error: "type is required" });
  const payload    = { type, data: data ?? {}, timestamp: Date.now() };
  const recipients = clients.broadcast(payload);
  res.json({ status: "broadcast", recipients });
});

// 404 fallback
app.use((_req, res) => res.status(404).json({ error: "not found" }));

// ── Boot ──────────────────────────────────────────────────────────────────────

server.listen(WS_PORT, async () => {
  console.log(`[server] WebSocket + REST listening on port ${WS_PORT}`);
  // Start Kafka listener in background (auto-reconnects)
  startKafkaListener(clients).catch((err) =>
    console.error("[server] Kafka listener fatal:", err)
  );
});