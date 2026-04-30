/**
 * message_handler.js
 * Processes inbound WebSocket messages from clients and formats
 * outbound Kafka → WebSocket payloads.
 */

/** @typedef {import("./client_manager").ClientManager} ClientManager */

// ── Kafka topic → WS message type mapping ────────────────────────────────────

const TOPIC_TYPE_MAP = {
  "drone.telemetry":            "telemetry",
  "drone.detections.objects":   "detection",
  "drone.navigation.result":    "navigation",
  "drone.commands.feedback":    "command",
  "drone.feedback.spoken":      "feedback",
};

// ── Outbound (Kafka → client) ─────────────────────────────────────────────────

/**
 * Format a raw Kafka message into the standard WebSocket envelope.
 * @param {string} topic
 * @param {object} data
 * @returns {object}
 */
function formatKafkaMessage(topic, data) {
  return {
    type:      TOPIC_TYPE_MAP[topic] ?? "unknown",
    topic,
    data,
    timestamp: Date.now(),
  };
}

// ── Inbound (client → server) ─────────────────────────────────────────────────

/**
 * Handle a raw text message received from a connected client.
 * @param {string}        rawMessage
 * @param {string}        clientId
 * @param {ClientManager} clients
 * @returns {{ reply: object|null, broadcast: object|null }}
 */
function handleClientMessage(rawMessage, clientId, clients) {
  let parsed;
  try {
    parsed = JSON.parse(rawMessage);
  } catch {
    console.warn(`[msg-handler] non-JSON from ${clientId}: ${rawMessage.slice(0, 80)}`);
    return { reply: _error("invalid JSON"), broadcast: null };
  }

  const { type, data, timestamp } = parsed;

  switch (type) {
    case "subscribe": {
      const types = Array.isArray(data?.types) ? data.types : [];
      clients.setFilter(clientId, types);
      return {
        reply: { type: "subscribed", filter: types, timestamp: Date.now() },
        broadcast: null,
      };
    }

    case "ping":
      return {
        reply: { type: "pong", timestamp: timestamp ?? Date.now() },
        broadcast: null,
      };

    case "request_status":
      return {
        reply: {
          type:      "status",
          clients:   clients.size,
          timestamp: Date.now(),
        },
        broadcast: null,
      };

    default:
      console.warn(`[msg-handler] unknown type "${type}" from ${clientId}`);
      return { reply: _error(`unknown type: ${type}`), broadcast: null };
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function _error(reason) {
  return { type: "error", reason, timestamp: Date.now() };
}

module.exports = { formatKafkaMessage, handleClientMessage, TOPIC_TYPE_MAP };