/**
 * InfluxDB Client Singleton
 * Wraps @influxdata/influxdb-client with convenience query helpers
 */

'use strict';

const { InfluxDB, Point } = require('@influxdata/influxdb-client');
const logger = require('../utils/logger');

require('dotenv').config();

const INFLUX_URL    = process.env.INFLUXDB_URL    || 'http://localhost:8086';
const INFLUX_TOKEN  = process.env.INFLUXDB_TOKEN  || 'drone-telemetry-token';
const INFLUX_ORG    = process.env.INFLUXDB_ORG    || 'drone-project';
const INFLUX_BUCKET = process.env.INFLUXDB_BUCKET || 'drone_telemetry';

const influx = new InfluxDB({ url: INFLUX_URL, token: INFLUX_TOKEN });

const queryApi = influx.getQueryApi(INFLUX_ORG);
const writeApi = influx.getWriteApi(INFLUX_ORG, INFLUX_BUCKET, 'ms');

// ─── Health Check ─────────────────────────────────────────────────────────────
const checkHealth = async () => {
  try {
    const rows = [];
    await queryApi.collectRows(`
      from(bucket: "${INFLUX_BUCKET}")
        |> range(start: -1m)
        |> limit(n: 1)
    `);
    return { connected: true, url: INFLUX_URL, bucket: INFLUX_BUCKET, org: INFLUX_ORG };
  } catch (err) {
    return { connected: false, error: err.message };
  }
};

/**
 * Run a raw Flux query and return rows as an array of objects.
 * @param {string} fluxQuery
 * @returns {Promise<Array>}
 */
const query = async (fluxQuery) => {
  const rows = [];
  return new Promise((resolve, reject) => {
    queryApi.queryRows(fluxQuery, {
      next(row, tableMeta) {
        rows.push(tableMeta.toObject(row));
      },
      error(err) {
        logger.error('InfluxDB query error:', err.message);
        reject(err);
      },
      complete() {
        resolve(rows);
      },
    });
  });
};

/**
 * Write a single data point to InfluxDB.
 * @param {Point} point
 */
const writePoint = async (point) => {
  try {
    writeApi.writePoint(point);
    await writeApi.flush();
  } catch (err) {
    logger.error('InfluxDB write error:', err.message);
    throw err;
  }
};

/**
 * Write multiple points (batch).
 * @param {Point[]} points
 */
const writePoints = async (points) => {
  try {
    writeApi.writePoints(points);
    await writeApi.flush();
  } catch (err) {
    logger.error('InfluxDB batch write error:', err.message);
    throw err;
  }
};

module.exports = {
  influx,
  queryApi,
  writeApi,
  query,
  writePoint,
  writePoints,
  checkHealth,
  Point,
  INFLUX_BUCKET,
  INFLUX_ORG,
};
