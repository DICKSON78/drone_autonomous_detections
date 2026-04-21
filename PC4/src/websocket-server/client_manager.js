const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');

/**
 * Manages connected WebSocket clients, subscriptions, and broadcasting.
 */
class ClientManager {
  constructor() {
    this._clients = new Map(); // clientId → { ws, ip, connectedAt, filter }
  }

  addClient(ws, req) {
    const clientId = uuidv4().slice(0, 8);
    const ip       = req.socket.remoteAddress;
    this._clients.set(clientId, {
      ws,
      ip,
      connectedAt: Date.now(),
      filter: []          // empty = receive all types
    });
    return clientId;
  }

  removeClient(clientId) {
    this._clients.delete(clientId);
  }

  setFilter(clientId, types) {
    const client = this._clients.get(clientId);
    if (client) client.filter = types;
  }

  sendToClient(clientId, message) {
    const client = this._clients.get(clientId);
    if (client && client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  broadcast(message) {
    let sent = 0;
    const payload = JSON.stringify(message);
    for (const [, client] of this._clients) {
      if (client.ws.readyState !== WebSocket.OPEN) continue;
      // Respect per-client type filter
      if (client.filter.length > 0 && !client.filter.includes(message.type)) continue;
      try {
        client.ws.send(payload);
        sent++;
      } catch (e) {
        console.error('[ClientManager] Send error:', e.message);
      }
    }
    return sent;
  }

  count() {
    return this._clients.size;
  }

  list() {
    return [...this._clients.entries()].map(([id, c]) => ({
      id,
      ip:          c.ip,
      connectedAt: c.connectedAt,
      filter:      c.filter
    }));
  }
}

module.exports = new ClientManager();