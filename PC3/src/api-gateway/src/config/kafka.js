/**
 * Kafka Client Configuration
 * KafkaJS singleton shared across producer and consumer services
 */

'use strict';

const { Kafka, logLevel } = require('kafkajs');
const logger = require('../utils/logger');

require('dotenv').config();

const brokers = (process.env.KAFKA_BROKERS || 'localhost:9092').split(',');
const clientId = process.env.KAFKA_CLIENT_ID || 'pc3-api-gateway';

const kafka = new Kafka({
  clientId,
  brokers,
  retry: {
    initialRetryTime: 300,
    retries: 10,
  },
  logLevel: logLevel.WARN,
  logCreator: () => ({ namespace, level, label, log }) => {
    const { message } = log;
    if (level === logLevel.ERROR) logger.error(`[Kafka][${namespace}] ${message}`);
    else if (level === logLevel.WARN)  logger.warn(`[Kafka][${namespace}] ${message}`);
  },
});

// ─── Topic Constants ──────────────────────────────────────────────────────────
const TOPICS = {
  GPS:         process.env.KAFKA_TOPIC_GPS         || 'drone.telemetry.gps',
  BATTERY:     process.env.KAFKA_TOPIC_BATTERY     || 'drone.telemetry.battery',
  ATTITUDE:    process.env.KAFKA_TOPIC_ATTITUDE    || 'drone.telemetry.attitude',
  VELOCITY:    process.env.KAFKA_TOPIC_VELOCITY    || 'drone.telemetry.velocity',
  FLIGHT:      process.env.KAFKA_TOPIC_FLIGHT      || 'drone.telemetry.flight',
  DETECTIONS:  process.env.KAFKA_TOPIC_DETECTIONS  || 'drone.detections.objects',
  NAVIGATION:  process.env.KAFKA_TOPIC_NAVIGATION  || 'drone.navigation.decisions',
  COMMANDS:    process.env.KAFKA_TOPIC_COMMANDS    || 'drone.commands.flight',
  STATUS:      process.env.KAFKA_TOPIC_STATUS      || 'drone.status.flight',
  ALERTS:      process.env.KAFKA_TOPIC_ALERTS      || 'drone.alerts.critical',
  FEEDBACK:    process.env.KAFKA_TOPIC_FEEDBACK    || 'drone.feedback.messages',
  SYSTEM:      process.env.KAFKA_TOPIC_SYSTEM      || 'drone.status.system',
};

// ─── Shared producer ─────────────────────────────────────────────────────────
let _producer = null;

const getProducer = async () => {
  if (_producer) return _producer;
  _producer = kafka.producer();
  await _producer.connect();
  logger.info('[Kafka] Producer connected');
  return _producer;
};

module.exports = { kafka, TOPICS, getProducer };
