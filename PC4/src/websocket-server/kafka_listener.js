/**
 * kafka_listener.js
 * Connects to Kafka, subscribes to all drone topics, and relays messages
 * to connected WebSocket clients via the ClientManager.
 */

const { Kafka, logLevel } = require("kafkajs");
const { formatKafkaMessage, TOPIC_TYPE_MAP } = require("./message_handler");

/** @typedef {import("./client_manager").ClientManager} ClientManager */

const KAFKA_BROKER  = process.env.KAFKA_BROKER || "kafka:9092";
const RETRY_DELAY_MS = 10_000;

/**
 * Start the Kafka listener. Reconnects automatically on failure.
 * @param {ClientManager} clients
 */
async function startKafkaListener(clients) {
  const kafka = new Kafka({
    clientId:  "websocket-server",
    brokers:   [KAFKA_BROKER],
    logLevel:  logLevel.WARN,
    retry: {
      initialRetryTime: 3000,
      retries: 10,
    },
  });

  const consumer = kafka.consumer({ groupId: "websocket-server-group" });

  // Graceful shutdown
  const shutdown = async () => {
    try { await consumer.disconnect(); } catch { /* ignore */ }
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT",  shutdown);

  while (true) {
    try {
      await consumer.connect();
      console.log(`[kafka] connected to ${KAFKA_BROKER}`);

      const topics = Object.keys(TOPIC_TYPE_MAP);
      await consumer.subscribe({ topics, fromBeginning: false });
      console.log(`[kafka] subscribed to: ${topics.join(", ")}`);

      await consumer.run({
        eachMessage: async ({ topic, message }) => {
          let data;
          try {
            data = JSON.parse(message.value?.toString() ?? "{}");
          } catch {
            data = { raw: message.value?.toString() };
          }

          const payload  = formatKafkaMessage(topic, data);
          const count    = clients.broadcast(payload);
          console.log(`[kafka] relayed  topic=${topic}  clients=${count}`);
        },
      });
    } catch (err) {
      console.error(`[kafka] error: ${err.message} — retry in ${RETRY_DELAY_MS / 1000}s`);
      try { await consumer.disconnect(); } catch { /* ignore */ }
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
    }
  }
}

module.exports = { startKafkaListener };