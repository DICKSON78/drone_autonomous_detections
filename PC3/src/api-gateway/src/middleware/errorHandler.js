/**
 * Error Handler Middleware
 * Centralised error formatting — always returns consistent JSON
 */

'use strict';

const logger = require('../utils/logger');

const errorHandler = (err, req, res, next) => {
  const status  = err.status || err.statusCode || 500;
  const message = err.message || 'Internal Server Error';

  // Log 5xx as errors, 4xx as warnings
  if (status >= 500) {
    logger.error(`[${req.method}] ${req.path} → ${status}: ${message}`, { stack: err.stack });
  } else {
    logger.warn(`[${req.method}] ${req.path} → ${status}: ${message}`);
  }

  res.status(status).json({
    error:     message,
    status,
    path:      req.path,
    method:    req.method,
    timestamp: new Date().toISOString(),
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  });
};

module.exports = errorHandler;
