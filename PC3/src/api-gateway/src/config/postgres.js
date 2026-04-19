/**
 * PostgreSQL Client Config
 * Used for relational data like Mission History and Logs
 */

'use strict';

const { Pool } = require('pg');
const logger = require('../utils/logger');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://fyp_user:fyp_pass@localhost:5432/fyp_db',
});

// ─── Verification ─────────────────────────────────────────────────────────────
pool.on('connect', () => {
  logger.debug('[Postgres] Connected to database');
});

pool.on('error', (err) => {
  logger.error('[Postgres] Unexpected error on idle client', err);
});

/**
 * Initialize schemas
 */
const initDb = async () => {
  const client = await pool.connect();
  try {
    logger.info('[Postgres] Initializing schemas...');
    
    // Mission History Table
    await client.query(`
      CREATE TABLE IF NOT EXISTS mission_history (
        id SERIAL PRIMARY KEY,
        mission_id VARCHAR(50) UNIQUE NOT NULL,
        drone_id VARCHAR(50) NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        status VARCHAR(20) DEFAULT 'in_progress',
        waypoints JSONB,
        summary JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // System Logs Table
    await client.query(`
      CREATE TABLE IF NOT EXISTS system_event_logs (
        id SERIAL PRIMARY KEY,
        drone_id VARCHAR(50),
        event_type VARCHAR(50),
        severity VARCHAR(20),
        message TEXT,
        metadata JSONB,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    logger.info('[Postgres] Initialization complete');
  } catch (err) {
    logger.error('[Postgres] Initialization failed', err);
  } finally {
    client.release();
  }
};

module.exports = {
  query: (text, params) => pool.query(text, params),
  initDb,
  pool
};
