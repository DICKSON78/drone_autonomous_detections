/**
 * Command Service
 * Sends flight commands to PC1 via Kafka topic: drone.commands.flight
 * Validates commands before publishing.
 */

'use strict';

const { getProducer, TOPICS } = require('../config/kafka');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');

// ─── Allowed command types & required fields ───────────────────────────────────
const COMMAND_SCHEMA = {
  arm:      [],
  disarm:   [],
  takeoff:  ['altitude'],
  land:     [],
  goto:     ['latitude', 'longitude'],
  rtl:      [],    // Return To Launch
  hold:     [],
  mission:  ['waypoints'],
  emergency_stop: [],
};

/**
 * Validate and publish a flight command.
 * @param {object} command  - { type, drone_id, ...params }
 * @returns {object}        - { success, commandId, message }
 */
const sendCommand = async (command) => {
  const { type, drone_id = 'drone_001', ...params } = command;

  // Validate command type
  if (!COMMAND_SCHEMA.hasOwnProperty(type)) {
    throw new Error(`Unknown command type: "${type}". Allowed: ${Object.keys(COMMAND_SCHEMA).join(', ')}`);
  }

  // Validate required fields
  const required = COMMAND_SCHEMA[type];
  for (const field of required) {
    if (params[field] === undefined || params[field] === null) {
      throw new Error(`Command "${type}" requires field: "${field}"`);
    }
  }

  // Validate specific ranges
  if (type === 'takeoff') {
    const alt = parseFloat(params.altitude);
    if (isNaN(alt) || alt < 1 || alt > 120) {
      throw new Error('takeoff altitude must be between 1m and 120m');
    }
  }
  if (type === 'goto') {
    const lat = parseFloat(params.latitude);
    const lon = parseFloat(params.longitude);
    if (isNaN(lat) || lat < -90  || lat > 90)  throw new Error('Invalid latitude');
    if (isNaN(lon) || lon < -180 || lon > 180) throw new Error('Invalid longitude');
  }

  const commandId = uuidv4();
  const payload = {
    command_id: commandId,
    drone_id,
    type,
    ...params,
    issued_by: 'pc3-api-gateway',
    timestamp: Date.now(),
  };

  const producer = await getProducer();
  await producer.send({
    topic: TOPICS.COMMANDS,
    messages: [
      {
        key: drone_id,
        value: JSON.stringify(payload),
      },
    ],
  });

  logger.info(`[Commands] Sent command: type=${type} drone=${drone_id} id=${commandId}`);

  return {
    success: true,
    commandId,
    message: `Command "${type}" sent to drone ${drone_id}`,
    payload,
  };
};

/**
 * Get list of all valid command types.
 */
const getCommandTypes = () =>
  Object.entries(COMMAND_SCHEMA).map(([type, required]) => ({ type, required }));

module.exports = { sendCommand, getCommandTypes };
