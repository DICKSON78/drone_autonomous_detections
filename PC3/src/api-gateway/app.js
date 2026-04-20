/**
 * PC3 - Drone Autonomous System
 * API Gateway - Main Entry Point
 * 
 * Responsibilities:
 *  - REST API for telemetry queries and drone commands
 *  - WebSocket server for real-time telemetry streaming
 *  - Kafka consumer (bridges Kafka -> WebSocket -> Frontend)
 *  - InfluxDB query interface
 *  - Health monitoring of all PC3 services
 */

'use strict';

const http = require('http');
const app = require('./src/app');
const { initWebSocketServer } = require('./src/services/websocketService');
const { initKafkaConsumer } = require('./src/services/kafkaService');
const logger = require('./src/utils/logger');

require('dotenv').config();

const PORT = process.env.PORT || 3001;
const HOST = process.env.HOST || '0.0.0.0';

// Create HTTP server (shared between Express + WebSocket)
const server = http.createServer(app);

// Attach WebSocket server to same HTTP server
initWebSocketServer(server);

// Start server
server.listen(PORT, HOST, async () => {
  logger.info('='.repeat(60));
  logger.info('  PC3 - TELEMETRY & DASHBOARD API GATEWAY STARTED');
  logger.info('='.repeat(60));
  logger.info(`  HTTP  : http://${HOST}:${PORT}`);
  logger.info(`  WS    : ws://${HOST}:${PORT}`);
  logger.info(`  ENV   : ${process.env.NODE_ENV || 'development'}`);
  logger.info('='.repeat(60));

  // Start Kafka consumer after server is up
  try {
    await initKafkaConsumer();
    logger.info('  Kafka consumers initialized');
  } catch (err) {
    logger.warn(`  Kafka not available yet: ${err.message} - will retry`);
  }
});

// Graceful shutdown
const shutdown = async (signal) => {
  logger.info(`Received ${signal}. Shutting down gracefully...`);
  server.close(() => {
    logger.info('HTTP server closed');
    process.exit(0);
  });
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('uncaughtException', (err) => {
  logger.error('Uncaught Exception:', err);
  process.exit(1);
});
process.on('unhandledRejection', (reason) => {
  logger.error('Unhandled Rejection:', reason);
});
