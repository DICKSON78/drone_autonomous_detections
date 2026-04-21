/**
 * message_handler.js
 * Formats Kafka payloads into WebSocket messages and handles
 * messages sent from dashboard clients.
 */

// ── Kafka → WebSocket formatting ──────────────────────────────────────────────

function formatKafkaMessage(type, data, topic) {
  return {
    type,
    topic,
    data,
    timestamp: Date.now()
  };
}

// ── Client → Server message handling ─────────────────────────────────────────

function handleClientMessage(msg, clientId, clientManager) {
  const { type, data } = msg;

  switch (type) {
    case 'ping':
      clientManager.sendToClient(clientId, { type: 'pong', timestamp: Date.now() });
      break;

    case 'subscribe':
      // Client requests filtered subscription to specific message types
      clientManager.setFilter(clientId, data?.types || []);
      clientManager.sendToClient(clientId, {
        type: 'subscribed',
        types: data?.types,
        timestamp: Date.now()
      });
      break;

    case 'request_status':
      clientManager.sendToClient(clientId, {
        type: 'status',
        clients: clientManager.count(),
        timestamp: Date.now()
      });
      break;

    default:
      console.warn(`[WS] Unknown message type '${type}' from ${clientId}`);
  }
}

// ── Alert classification ──────────────────────────────────────────────────────

function classifyAlert(detectionData) {
  const detections = detectionData?.detections || [];
  const critical   = detections.filter(d =>
    ['person', 'car', 'truck', 'bus'].includes(d.class_name) && d.confidence > 0.65
  );
  return critical.length > 0 ? 'high' : 'normal';
}

module.exports = { formatKafkaMessage, handleClientMessage, classifyAlert };