/**
 * client_manager.js
 * Tracks every connected WebSocket client, handles per-client subscriptions,
 * and provides broadcast helpers.
 */

const { v4: uuidv4 } = require("uuid");

class ClientManager {
  constructor() {
    /** @type {Map<string, ClientRecord>} */
    this._clients = new Map();
  }

  // ── Lifecycle ────────────────────────────────────────────────────────────

  /**
   * Register a new WebSocket connection.
   * @param {import("ws").WebSocket} ws
   * @param {import("http").IncomingMessage} req
   * @returns {string} Assigned client ID
   */
  add(ws, req) {
    const id = uuidv4().slice(0, 8);
    const ip =
      req.headers["x-forwarded-for"]?.split(",")[0].trim() ||
      req.socket?.remoteAddress ||
      "unknown";

    /** @type {ClientRecord} */
    const record = {
      id,
      ws,
      ip,
      connectedAt: Date.now(),
      filter: [],        // empty = receive all message types
      messageCount: 0,
    };

    this._clients.set(id, record);
    console.log(`[client-manager] connected  id=${id}  ip=${ip}  total=${this._clients.size}`);
    return id;
  }

  /**
   * Remove a client by ID.
   * @param {string} id
   */
  remove(id) {
    if (this._clients.delete(id)) {
      console.log(`[client-manager] disconnected  id=${id}  total=${this._clients.size}`);
    }
  }

  /**
   * Update the message-type filter for a client.
   * An empty array means "subscribe to everything".
   * @param {string} id
   * @param {string[]} types
   */
  setFilter(id, types) {
    const record = this._clients.get(id);
    if (!record) return;
    record.filter = Array.isArray(types) ? types : [];
    console.log(`[client-manager] filter updated  id=${id}  types=${record.filter.join(",") || "all"}`);
  }

  // ── Sending ───────────────────────────────────────────────────────────────

  /**
   * Send a message object to a single client.
   * @param {string} id
   * @param {object} payload
   */
  send(id, payload) {
    const record = this._clients.get(id);
    if (!record) return;
    this._sendToRecord(record, payload);
  }

  /**
   * Broadcast a message to all clients whose filter allows *type*.
   * @param {object} payload  Must contain a `type` field.
   * @returns {number} Number of recipients
   */
  broadcast(payload) {
    const type = payload?.type;
    let count = 0;

    for (const record of this._clients.values()) {
      const allowed =
        record.filter.length === 0 || record.filter.includes(type);
      if (allowed) {
        this._sendToRecord(record, payload);
        count++;
      }
    }

    return count;
  }

  // ── Queries ───────────────────────────────────────────────────────────────

  get size() {
    return this._clients.size;
  }

  /**
   * Serialisable info for the /clients endpoint.
   * @returns {object[]}
   */
  list() {
    return Array.from(this._clients.values()).map((r) => ({
      id:           r.id,
      ip:           r.ip,
      connectedAt:  r.connectedAt,
      filter:       r.filter,
      messageCount: r.messageCount,
    }));
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  _sendToRecord(record, payload) {
    const { ws } = record;
    if (ws.readyState !== 1 /* OPEN */) return;
    try {
      ws.send(JSON.stringify(payload));
      record.messageCount++;
    } catch (err) {
      console.error(`[client-manager] send error  id=${record.id}:`, err.message);
    }
  }
}

module.exports = { ClientManager };