/**
 * Request Logger Middleware
 * Adds a unique request-id header and logs latency for every request
 */

'use strict';

const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');

const requestLogger = (req, res, next) => {
  const requestId = uuidv4().slice(0, 8);
  const start = Date.now();

  req.requestId = requestId;
  res.setHeader('X-Request-ID', requestId);

  res.on('finish', () => {
    const ms = Date.now() - start;
    const level = res.statusCode >= 500 ? 'error' : res.statusCode >= 400 ? 'warn' : 'debug';
    logger[level](
      `[${requestId}] ${req.method} ${req.originalUrl} → ${res.statusCode} (${ms}ms)`
    );
  });

  next();
};

module.exports = requestLogger;
