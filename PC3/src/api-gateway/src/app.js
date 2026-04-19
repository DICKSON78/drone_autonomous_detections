/**
 * Express Application Setup
 * Registers middleware, routes, error handlers
 */

'use strict';

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');

const logger = require('./utils/logger');
const errorHandler = require('./middleware/errorHandler');
const requestLogger = require('./middleware/requestLogger');
const { initDb } = require('./config/postgres');

// Route imports
const telemetryRoutes = require('./routes/telemetry');
const commandRoutes = require('./routes/commands');
const dashboardRoutes = require('./routes/dashboard');
const analyticsRoutes = require('./routes/analytics');
const healthRoutes = require('./routes/health');
const alertRoutes = require('./routes/alerts');
const missionRoutes = require('./routes/missions');

require('dotenv').config();

const app = express();

// ─── Security & Performance Middleware ────────────────────────────────────────
app.use(helmet({ contentSecurityPolicy: false }));
app.use(compression());

// ─── CORS ─────────────────────────────────────────────────────────────────────
const allowedOrigins = (process.env.CORS_ORIGINS || '')
  .split(',')
  .map((o) => o.trim())
  .filter(Boolean);

app.use(
  cors({
    origin: (origin, cb) => {
      if (!origin || allowedOrigins.length === 0 || allowedOrigins.includes(origin)) {
        cb(null, true);
      } else {
        cb(new Error(`CORS: origin ${origin} not allowed`));
      }
    },
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Drone-ID'],
    credentials: true,
  })
);

// ─── Body Parsing ─────────────────────────────────────────────────────────────
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

// ─── HTTP Logging ─────────────────────────────────────────────────────────────
app.use(morgan('combined', { stream: { write: (msg) => logger.http(msg.trim()) } }));
app.use(requestLogger);

// ─── Rate Limiting ────────────────────────────────────────────────────────────
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 60_000,
  max: parseInt(process.env.RATE_LIMIT_MAX) || 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please slow down.' },
});
app.use('/api/', limiter);

// ─── API Routes ───────────────────────────────────────────────────────────────
app.use('/api/health', healthRoutes);
app.use('/api/telemetry', telemetryRoutes);
app.use('/api/commands', commandRoutes);
app.use('/api/dashboard', dashboardRoutes);
app.use('/api/analytics', analyticsRoutes);
app.use('/api/alerts', alertRoutes);
app.use('/api/missions', missionRoutes);

// ─── Initialize DB (async, non-blocking startup) ──────────────────────────────
initDb().catch(err => console.error('Postgres Init Fail:', err));

// ─── Root info endpoint ───────────────────────────────────────────────────────
app.get('/', (req, res) => {
  res.json({
    service: 'PC3 - Drone Telemetry & Dashboard API Gateway',
    version: '1.0.0',
    status: 'running',
    endpoints: {
      health: '/api/health',
      telemetry: '/api/telemetry',
      commands: '/api/commands',
      dashboard: '/api/dashboard',
      analytics: '/api/analytics',
      alerts: '/api/alerts',
      websocket: 'ws://localhost:3001',
    },
    timestamp: new Date().toISOString(),
  });
});

// ─── 404 Handler ─────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ error: `Route ${req.method} ${req.path} not found` });
});

// ─── Global Error Handler ─────────────────────────────────────────────────────
app.use(errorHandler);

module.exports = app;
