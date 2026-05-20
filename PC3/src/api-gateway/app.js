const express = require('express');
const { Kafka } = require('kafkajs');
const { InfluxDB } = require('@influxdata/influxdb-client');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// ── Configuration ──
const PORT = process.env.PORT || 8008;
const KAFKA_BROKERS = (process.env.KAFKA_BOOTSTRAP_SERVERS || 'kafka:9092').split(',');
const INFLUXDB_URL = process.env.INFLUXDB_URL || 'http://influxdb:8086';
const INFLUXDB_TOKEN = process.env.INFLUXDB_TOKEN || 'drone-telemetry-token';
const INFLUXDB_ORG = process.env.INFLUXDB_ORG || 'drone-project';
const INFLUXDB_BUCKET = process.env.INFLUXDB_BUCKET || 'drone_telemetry';

// ── Kafka Setup ──
const kafka = new Kafka({ clientId: 'api-gateway', brokers: KAFKA_BROKERS });
const producer = kafka.producer();
const consumer = kafka.consumer({ groupId: 'api-gateway-group' });

// ── InfluxDB Setup ──
const influxDB = new InfluxDB({ url: INFLUXDB_URL, token: INFLUXDB_TOKEN });
const queryApi = influxDB.getQueryApi(INFLUXDB_ORG);
const writeApi = influxDB.getWriteApi(INFLUXDB_ORG, INFLUXDB_BUCKET);

// ── In-memory cache for latest telemetry ──
let latestTelemetry = {
    connected: false, armed: false, mode: 'UNKNOWN',
    lat: 0, lon: 0, alt: 0, battery: 0, heading: 0,
    speed: 0, satellites: 0, fix_type: 0,
    timestamp: null
};

// ── Kafka Consumer: listen for telemetry updates ──
async function startConsumer() {
    try {
        await consumer.connect();
        await consumer.subscribe({ topic: 'drone.telemetry.full', fromBeginning: false });
        await consumer.subscribe({ topic: 'drone.telemetry.gps', fromBeginning: false });
        await consumer.subscribe({ topic: 'drone.status.flight', fromBeginning: false });
        await consumer.subscribe({ topic: 'drone.detections', fromBeginning: false });

        await consumer.run({
            eachMessage: async ({ topic, message }) => {
                const data = JSON.parse(message.value.toString());
                if (topic === 'drone.telemetry.full' || topic === 'drone.telemetry.gps') {
                    latestTelemetry = { ...latestTelemetry, ...data, timestamp: new Date().toISOString() };
                }
                // Forward to InfluxDB
                const point = {
                    measurement: topic.split('.').pop(),
                    tags: { source: 'api-gateway' },
                    fields: data,
                    timestamp: new Date()
                };
                writeApi.writePoint(point);
            }
        });
        console.log('[api-gateway] Kafka consumer connected');
    } catch (err) {
        console.error('[api-gateway] Kafka consumer error:', err.message);
    }
}

// ── Startup ──
(async () => {
    try {
        await producer.connect();
        console.log('[api-gateway] Kafka producer connected');
    } catch (err) {
        console.warn('[api-gateway] Kafka producer unavailable:', err.message);
    }
    startConsumer();
})();

// ── Routes ──

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'api-gateway', telemetry_age: latestTelemetry.timestamp });
});

// Latest telemetry snapshot
app.get('/telemetry/latest', (req, res) => {
    res.json(latestTelemetry);
});

// Query InfluxDB for time-series data
app.get('/telemetry/history', async (req, res) => {
    try {
        const { metric = 'gps_telemetry', hours = 1 } = req.query;
        const fluxQuery = `
            from(bucket: "${INFLUXDB_BUCKET}")
                |> range(start: -${hours}h)
                |> filter(fn: (r) => r._measurement == "${metric}")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> limit(n: 5000)
        `;
        const rows = [];
        queryApi.queryRows(fluxQuery, {
            next(row, tableMeta) {
                const o = tableMeta.toObject(row);
                rows.push(o);
            },
            error(err) {
                console.error('[api-gateway] InfluxDB query error:', err.message);
                res.status(500).json({ error: err.message });
            },
            complete() {
                res.json({ metric, count: rows.length, data: rows });
            }
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Publish command to Kafka
app.post('/command', async (req, res) => {
    try {
        const { text, type, target_gps, altitude } = req.body;
        const command = {
            command_id: `cmd_${Date.now()}`,
            type: type || 'goto',
            raw_text: text || '',
            target_gps: target_gps || { lat: -6.1630, lon: 35.7516 },
            altitude: altitude || 10.0,
            timestamp: new Date().toISOString()
        };
        await producer.send({
            topic: 'drone.commands.flight',
            messages: [{ value: JSON.stringify(command) }]
        });
        res.json({ success: true, command });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Get obstacle/radar data (proxied from drone exporter)
app.get('/obstacles', async (req, res) => {
    try {
        const fetch = (await import('node-fetch')).default;
        const response = await fetch('http://host.docker.internal:8007/obstacles');
        const data = await response.json();
        res.json(data);
    } catch (err) {
        res.json({ count: 0, obstacles: [], error: 'drone exporter unavailable' });
    }
});

// Flight summary from InfluxDB
app.get('/summary', async (req, res) => {
    try {
        const fluxQuery = `
            from(bucket: "${INFLUXDB_BUCKET}")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "gps_telemetry")
                |> filter(fn: (r) => r._field == "altitude" or r._field == "battery")
                |> mean()
                |> pivot(rowKey:["_measurement"], columnKey: ["_field"], valueColumn: "_value")
        `;
        const rows = [];
        queryApi.queryRows(fluxQuery, {
            next(row, tableMeta) { rows.push(tableMeta.toObject(row)); },
            error(err) { res.status(500).json({ error: err.message }); },
            complete() { res.json({ summary: rows }); }
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ── Start ──
app.listen(PORT, '0.0.0.0', () => {
    console.log(`[api-gateway] Listening on port ${PORT}`);
    console.log(`[api-gateway] InfluxDB: ${INFLUXDB_URL}`);
    console.log(`[api-gateway] Kafka: ${KAFKA_BROKERS.join(', ')}`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    await writeApi.close();
    await producer.disconnect();
    await consumer.disconnect();
    process.exit(0);
});
