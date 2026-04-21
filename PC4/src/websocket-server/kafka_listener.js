const { Kafka } = require('kafkajs');

const kafka = new Kafka({
  clientId: 'pc4-websocket-server',
  brokers: [(process.env.KAFKA_BROKER || 'PC1:9092')]
});

const consumer = kafka.consumer({ groupId: 'websocket-server-group' });

// Topics to relay to the web dashboard
const TOPICS = [
  'drone.telemetry',
  'drone.detections.objects',
  'drone.navigation.result',
  'drone.commands.feedback',
  'drone.feedback.spoken',
];

// Map Kafka topic → WebSocket message type
const TOPIC_TYPE_MAP = {
  'drone.telemetry':            'telemetry',
  'drone.detections.objects':   'detection',
  'drone.navigation.result':    'navigation',
  'drone.commands.feedback':    'command',
  'drone.feedback.spoken':      'feedback',
};

async function start(clientManager, messageHandler) {
  try {
    await consumer.connect();
    console.log('[Kafka] Consumer connected');

    await consumer.subscribe({ topics: TOPICS, fromBeginning: false });

    await consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        try {
          const value = JSON.parse(message.value.toString());
          const type  = TOPIC_TYPE_MAP[topic] || 'unknown';

          const wsMessage = messageHandler.formatKafkaMessage(type, value, topic);
          const count = clientManager.broadcast(wsMessage);

          if (count > 0) {
            console.log(`[Kafka→WS] ${topic} → ${count} clients`);
          }
        } catch (e) {
          console.error(`[Kafka] Parse error on ${topic}:`, e.message);
        }
      }
    });
  } catch (e) {
    console.error('[Kafka] Connection failed:', e.message);
    console.log('[Kafka] Retrying in 5s…');
    setTimeout(() => start(clientManager, messageHandler), 5000);
  }
}

module.exports = { start };