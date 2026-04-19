/**
 * Mission History Service
 * Handles relational storage for flight missions
 */

'use strict';

const db = require('../config/postgres');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');

/**
 * Start a new mission
 */
const startMission = async (drone_id, waypoints = []) => {
  const mission_id = `MSN-${Date.now()}`;
  const query = `
    INSERT INTO mission_history (mission_id, drone_id, start_time, waypoints, status)
    VALUES ($1, $2, CURRENT_TIMESTAMP, $3, 'active')
    RETURNING *
  `;
  const values = [mission_id, drone_id, JSON.stringify(waypoints)];
  
  const res = await db.query(query, values);
  logger.info(`[Mission] Started mission ${mission_id} for drone ${drone_id}`);
  return res.rows[0];
};

/**
 * End a mission and save summary
 */
const endMission = async (mission_id, summary = {}) => {
  const query = `
    UPDATE mission_history 
    SET end_time = CURRENT_TIMESTAMP, status = 'completed', summary = $1
    WHERE mission_id = $2
    RETURNING *
  `;
  const values = [JSON.stringify(summary), mission_id];
  
  const res = await db.query(query, values);
  if (res.rowCount === 0) throw new Error('Mission not found');
  
  logger.info(`[Mission] Ended mission ${mission_id}`);
  return res.rows[0];
};

/**
 * Get all missions for a drone
 */
const getMissions = async (drone_id = null) => {
  let query = 'SELECT * FROM mission_history';
  let params = [];

  if (drone_id) {
    query += ' WHERE drone_id = $1';
    params.push(drone_id);
  }

  query += ' ORDER BY start_time DESC LIMIT 50';
  
  const res = await db.query(query, params);
  return res.rows;
};

/**
 * Log a system event
 */
const logEvent = async (drone_id, type, severity, message, metadata = {}) => {
  const query = `
    INSERT INTO system_event_logs (drone_id, event_type, severity, message, metadata)
    VALUES ($1, $2, $3, $4, $5)
  `;
  const values = [drone_id, type, severity, message, JSON.stringify(metadata)];
  await db.query(query, values);
};

module.exports = {
  startMission,
  endMission,
  getMissions,
  logEvent
};
