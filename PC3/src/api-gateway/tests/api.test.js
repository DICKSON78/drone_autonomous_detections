/**
 * API Gateway Integration Tests
 * Tests all Express routes with mocked InfluxDB + Kafka
 */

'use strict';

const request = require('supertest');
const app     = require('../src/app');

// ─── Mock InfluxDB ─────────────────────────────────────────────────────────
jest.mock('../src/config/influxdb', () => ({
  query:       jest.fn().mockResolvedValue([]),
  writePoint:  jest.fn().mockResolvedValue(undefined),
  writePoints: jest.fn().mockResolvedValue(undefined),
  checkHealth: jest.fn().mockResolvedValue({ connected: true, url: 'http://localhost:8086' }),
  Point:       require('@influxdata/influxdb-client').Point,
  INFLUX_BUCKET: 'drone_telemetry',
  INFLUX_ORG:    'drone-project',
}));

// ─── Mock Kafka ────────────────────────────────────────────────────────────
jest.mock('../src/config/kafka', () => ({
  kafka: { admin: jest.fn(() => ({ connect: jest.fn(), listTopics: jest.fn().mockResolvedValue([]), disconnect: jest.fn() })) },
  TOPICS: {
    GPS: 'drone.telemetry.gps', BATTERY: 'drone.telemetry.battery',
    COMMANDS: 'drone.commands.flight',
  },
  getProducer: jest.fn().mockResolvedValue({
    send: jest.fn().mockResolvedValue(undefined),
  }),
}));

// ─── Mock WebSocket service ────────────────────────────────────────────────
jest.mock('../src/services/websocketService', () => ({
  initWebSocketServer: jest.fn(),
  broadcast:           jest.fn(),
  broadcastAlert:      jest.fn(),
  getStats:            jest.fn().mockReturnValue({ connectedClients: 0, clientIds: [] }),
}));

// ─── Mock Alert service ───────────────────────────────────────────────────
jest.mock('../src/services/alertService', () => ({
  evaluate:        jest.fn().mockResolvedValue(undefined),
  getActiveAlerts: jest.fn().mockReturnValue([]),
  reloadRules:     jest.fn(),
}));

// ═══════════════════════════════════════════════════════════════════════════════

describe('Health Routes', () => {
  it('GET /api/health → 200 ok', async () => {
    const res = await request(app).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.service).toBe('pc3-api-gateway');
  });

  it('GET /api/health/detailed → 200 or 503', async () => {
    const res = await request(app).get('/api/health/detailed');
    expect([200, 503]).toContain(res.status);
    expect(res.body).toHaveProperty('checks');
  });
});

describe('Telemetry Routes', () => {
  it('GET /api/telemetry/gps → 200 with empty data', async () => {
    const res = await request(app).get('/api/telemetry/gps?range=1h&droneId=drone_001');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('data');
    expect(Array.isArray(res.body.data)).toBe(true);
  });

  it('GET /api/telemetry/battery → 200', async () => {
    const res = await request(app).get('/api/telemetry/battery?range=30m');
    expect(res.status).toBe(200);
  });

  it('GET /api/telemetry/attitude → 200', async () => {
    const res = await request(app).get('/api/telemetry/attitude');
    expect(res.status).toBe(200);
  });

  it('GET /api/telemetry/detections → 200', async () => {
    const res = await request(app).get('/api/telemetry/detections?range=1h');
    expect(res.status).toBe(200);
  });

  it('GET /api/telemetry/detections/summary → 200', async () => {
    const res = await request(app).get('/api/telemetry/detections/summary');
    expect(res.status).toBe(200);
  });

  it('GET /api/telemetry/navigation → 200', async () => {
    const res = await request(app).get('/api/telemetry/navigation');
    expect(res.status).toBe(200);
  });

  it('POST /api/telemetry → 201 with valid payload', async () => {
    const res = await request(app).post('/api/telemetry').send({
      drone_id: 'drone_001',
      data_type: 'gps',
      data: { latitude: -1.29, longitude: 36.82, altitude: 50, speed: 5 },
    });
    expect(res.status).toBe(201);
    expect(res.body.success).toBe(true);
  });

  it('POST /api/telemetry → 400 with invalid data_type', async () => {
    const res = await request(app).post('/api/telemetry').send({
      drone_id: 'drone_001',
      data_type: 'invalid',
      data: {},
    });
    expect(res.status).toBe(400);
  });

  it('POST /api/telemetry → 400 missing drone_id', async () => {
    const res = await request(app).post('/api/telemetry').send({
      data_type: 'gps',
      data: { latitude: 0 },
    });
    expect(res.status).toBe(400);
  });
});

describe('Command Routes', () => {
  it('GET /api/commands/types → 200 with list', async () => {
    const res = await request(app).get('/api/commands/types');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.commands)).toBe(true);
    expect(res.body.commands.length).toBeGreaterThan(0);
  });

  it('POST /api/commands → 202 takeoff command', async () => {
    const res = await request(app).post('/api/commands').send({
      type:      'takeoff',
      altitude:  20,
      drone_id:  'drone_001',
    });
    expect(res.status).toBe(202);
    expect(res.body.success).toBe(true);
    expect(res.body).toHaveProperty('commandId');
  });

  it('POST /api/commands → 202 goto command', async () => {
    const res = await request(app).post('/api/commands').send({
      type:      'goto',
      latitude:  -1.2921,
      longitude: 36.8219,
      altitude:  50,
      drone_id:  'drone_001',
    });
    expect(res.status).toBe(202);
  });

  it('POST /api/commands → 202 land command', async () => {
    const res = await request(app).post('/api/commands').send({ type: 'land' });
    expect(res.status).toBe(202);
  });

  it('POST /api/commands → 400 unknown type', async () => {
    const res = await request(app).post('/api/commands').send({ type: 'fly_backwards' });
    expect(res.status).toBe(400);
  });

  it('POST /api/commands → 400 takeoff missing altitude', async () => {
    const res = await request(app).post('/api/commands').send({ type: 'takeoff' });
    expect(res.status).toBe(400);
  });

  it('POST /api/commands → 400 altitude > 120m', async () => {
    const res = await request(app).post('/api/commands').send({ type: 'takeoff', altitude: 200 });
    expect(res.status).toBe(400);
  });

  it('POST /api/commands → 400 invalid lat/lon', async () => {
    const res = await request(app).post('/api/commands').send({
      type: 'goto', latitude: 999, longitude: -181,
    });
    expect(res.status).toBe(400);
  });
});

describe('Dashboard Routes', () => {
  it('GET /api/dashboard/summary → 200', async () => {
    const res = await request(app).get('/api/dashboard/summary?droneId=drone_001');
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
  });

  it('GET /api/dashboard/live → 200', async () => {
    const res = await request(app).get('/api/dashboard/live?droneId=drone_001');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('live');
    expect(res.body).toHaveProperty('activeAlerts');
    expect(res.body).toHaveProperty('websocket');
  });

  it('GET /api/dashboard/websocket-stats → 200', async () => {
    const res = await request(app).get('/api/dashboard/websocket-stats');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('connectedClients');
  });
});

describe('Analytics Routes', () => {
  it('GET /api/analytics/flight-stats → 200', async () => {
    const res = await request(app).get('/api/analytics/flight-stats?droneId=drone_001&range=24h');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('stats');
  });

  it('GET /api/analytics/detection-trends → 200', async () => {
    const res = await request(app).get('/api/analytics/detection-trends?range=24h');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('trends');
  });

  it('GET /api/analytics/battery-health → 200', async () => {
    const res = await request(app).get('/api/analytics/battery-health?range=24h');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('battery');
  });

  it('GET /api/analytics/path → 200', async () => {
    const res = await request(app).get('/api/analytics/path?droneId=drone_001&range=1h');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('path');
  });
});

describe('Alert Routes', () => {
  it('GET /api/alerts/active → 200', async () => {
    const res = await request(app).get('/api/alerts/active');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('alerts');
  });

  it('POST /api/alerts/rules/reload → 200', async () => {
    const res = await request(app).post('/api/alerts/rules/reload');
    expect(res.status).toBe(200);
  });
});

describe('404 Handling', () => {
  it('GET /api/nonexistent → 404', async () => {
    const res = await request(app).get('/api/nonexistent');
    expect(res.status).toBe(404);
  });
});
