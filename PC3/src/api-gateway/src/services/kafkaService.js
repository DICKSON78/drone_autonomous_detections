/**
 * Kafka Consumer Service
 * Subscribes to all drone telemetry topics and bridges them to:
 *  1. WebSocket broadcast  → real-time frontend updates
 *  2. InfluxDB write       → persistent time-series storage
 *  3. Alert evaluation     → rule-based alerting
 */

'use strict';

const { kafka, TOPICS } = require('../config/kafka');
const { writePoint, Point } = require('../config/influxdb');
const { broadcast, broadcastAlert } = require('./websocketService');
const alertService = require('./alertService');
const logger = require('../utils/logger');

require('dotenv').config();

const GROUP_ID = process.env.KAFKA_GROUP_ID || 'pc3-consumer-group';

let consumer = null;

// ─── Init ─────────────────────────────────────────────────────────────────────
const initKafkaConsumer = async () => {
  consumer = kafka.consumer({ groupId: GROUP_ID });

  await consumer.connect();
  logger.info('[Kafka] Consumer connected');

  // Subscribe to every telemetry topic
  const topicsToSubscribe = [
    TOPICS.GPS,
    TOPICS.BATTERY,
    TOPICS.ATTITUDE,
    TOPICS.VELOCITY,
    TOPICS.FLIGHT,
    TOPICS.DETECTIONS,
    TOPICS.NAVIGATION,
    TOPICS.STATUS,
    TOPICS.ALERTS,
    TOPICS.FEEDBACK,
    TOPICS.SYSTEM,
  ];

  for (const topic of topicsToSubscribe) {
    await consumer.subscribe({ topic, fromBeginning: false });
    logger.info(`[Kafka] Subscribed to topic: ${topic}`);
  }

  await consumer.run({
    eachMessage: async ({ topic, partition, message }) => {
      try {
        const raw = message.value?.toString();
        if (!raw) return;
        const data = JSON.parse(raw);
        await processMessage(topic, data);
      } catch (err) {
        logger.error(`[Kafka] Error processing message from ${topic}: ${err.message}`);
      }
    },
  });
};

// ─── Message Router ───────────────────────────────────────────────────────────
const processMessage = async (topic, data) => {
  switch (topic) {
    case TOPICS.GPS:
      await handleGps(data);
      break;
    case TOPICS.BATTERY:
      await handleBattery(data);
      break;
    case TOPICS.ATTITUDE:
      await handleAttitude(data);
      break;
    case TOPICS.VELOCITY:
      await handleVelocity(data);
      break;
    case TOPICS.FLIGHT:
      await handleFlight(data);
      break;
    case TOPICS.DETECTIONS:
      await handleDetections(data);
      break;
    case TOPICS.NAVIGATION:
      await handleNavigation(data);
      break;
    case TOPICS.STATUS:
      await handleStatus(data);
      break;
    case TOPICS.ALERTS:
      await handleAlert(data);
      break;
    case TOPICS.FEEDBACK:
      await handleFeedback(data);
      break;
    case TOPICS.SYSTEM:
      await handleSystem(data);
      break;
    default:
      logger.warn(`[Kafka] No handler for topic: ${topic}`);
  }
};

// ─── Handlers ─────────────────────────────────────────────────────────────────

const handleGps = async (data) => {
  const droneId = data.drone_id || 'drone_001';
  // Broadcast to WebSocket
  broadcast('gps', data);

  // Write to InfluxDB
  const point = new Point('gps_telemetry')
    .tag('drone_id', droneId)
    .tag('source_pc', 'PC1')
    .floatField('latitude',  parseFloat(data.latitude  || data.lat || 0))
    .floatField('longitude', parseFloat(data.longitude || data.lon || 0))
    .floatField('altitude',  parseFloat(data.altitude  || data.alt || 0))
    .floatField('speed',     parseFloat(data.speed || 0))
    .timestamp(new Date());

  await writePoint(point);

  // Check alert rules
  await alertService.evaluate('gps', data, droneId);
};

const handleBattery = async (data) => {
  const droneId = data.drone_id || 'drone_001';
  broadcast('battery', data);

  const point = new Point('battery_telemetry')
    .tag('drone_id', droneId)
    .tag('source_pc', 'PC1')
    .floatField('percentage',   parseFloat(data.percentage || data.remaining_percent || 0))
    .floatField('voltage',      parseFloat(data.voltage_v || data.voltage || 0))
    .floatField('current',      parseFloat(data.current_battery || data.current || 0))
    .floatField('temperature',  parseFloat(data.temperature_degc || data.temperature || 0))
    .timestamp(new Date());

  await writePoint(point);
  await alertService.evaluate('battery', data, droneId);
};

const handleAttitude = async (data) => {
  const droneId = data.drone_id || 'drone_001';
  broadcast('attitude', data);

  const point = new Point('attitude_telemetry')
    .tag('drone_id', droneId)
    .tag('source_pc', 'PC1')
    .floatField('roll_deg',  parseFloat(data.roll_deg  || 0))
    .floatField('pitch_deg', parseFloat(data.pitch_deg || 0))
    .floatField('yaw_deg',   parseFloat(data.yaw_deg   || 0))
    .timestamp(new Date());

  await writePoint(point);
};

const handleFlight = async (data) => {
  const droneId = data.drone_id || 'drone_001';
  broadcast('flight', data);

  const point = new Point('flight_status')
    .tag('drone_id', droneId)
    .tag('source_pc', 'PC1')
    .tag('is_armed',   String(data.is_armed   || false))
    .tag('is_flying',  String(data.is_flying  || false))
    .tag('flight_mode', data.flight_mode || 'unknown')
    .floatField('altitude_m', parseFloat(data.altitude || 0))
    .floatField('speed_ms',   parseFloat(data.speed    || 0))
    .timestamp(new Date());

  await writePoint(point);
};

const handleDetections = async (data) => {
  const droneId = data.drone_id || 'drone_001';
  broadcast('detections', data);

  const detections = Array.isArray(data.detections) ? data.detections : [];
  for (const det of detections) {
    const point = new Point('object_detections')
      .tag('drone_id',    droneId)
      .tag('source_pc',   'PC2')
      .tag('object_class', det.class_name || det.label || 'unknown')
      .floatField('confidence',  parseFloat(det.confidence || 0))
      .floatField('bbox_x',      parseFloat((det.bbox || [])[0] || 0))
      .floatField('bbox_y',      parseFloat((det.bbox || [])[1] || 0))
      .floatField('bbox_width',  parseFloat((det.bbox || [])[2] || 0))
      .floatField('bbox_height', parseFloat((det.bbox || [])[3] || 0))
      .timestamp(new Date());

    await writePoint(point);
  }
};

const handleNavigation = async (data) => {
  const droneId = data.drone_id || 'drone_001';
  broadcast('navigation', data);

  const point = new Point('navigation_telemetry')
    .tag('drone_id',   droneId)
    .tag('source_pc',  'PC2')
    .tag('next_action', data.next_action || 'unknown')
    .floatField('confidence',      parseFloat(data.confidence      || 0))
    .floatField('estimated_time',  parseFloat(data.estimated_time  || 0))
    .floatField('path_length',     parseFloat((data.path || []).length))
    .timestamp(new Date());

  await writePoint(point);
};

const handleStatus = async (data) => {
  broadcast('status', data);
  logger.info(`[Kafka][STATUS] drone=${data.drone_id} cmd=${data.command} status=${data.status}`);
};

const handleAlert = async (data) => {
  broadcast('alert', data);
  broadcastAlert(data);
  logger.warn(`[Kafka][ALERT] ${JSON.stringify(data)}`);
};

const handleVelocity = async (data) => {
  const droneId = data.drone_id || 'drone_001';
  broadcast('velocity', data);

  const point = new Point('velocity_telemetry')
    .tag('drone_id', droneId)
    .tag('source_pc', 'PC1')
    .floatField('north', parseFloat(data.north || 0))
    .floatField('east',  parseFloat(data.east  || 0))
    .floatField('down',  parseFloat(data.down  || 0))
    .floatField('speed', parseFloat(data.speed || 0))
    .timestamp(new Date());

  await writePoint(point);
};

const handleFeedback = async (data) => {
  broadcast('feedback', data);
  logger.info(`[Kafka][FEEDBACK] ${data.message || JSON.stringify(data)}`);
};

const handleSystem = async (data) => {
  const droneId = data.drone_id || 'drone_001';
  broadcast('system', data);

  const point = new Point('system_status')
    .tag('drone_id', droneId)
    .floatField('cpu_usage',    parseFloat(data.cpu_usage || 0))
    .floatField('memory_usage', parseFloat(data.memory_usage || 0))
    .timestamp(new Date());

  await writePoint(point);
};

// ─── Graceful shutdown ────────────────────────────────────────────────────────
const stopKafkaConsumer = async () => {
  if (consumer) {
    await consumer.disconnect();
    logger.info('[Kafka] Consumer disconnected');
  }
};

module.exports = { initKafkaConsumer, stopKafkaConsumer };
