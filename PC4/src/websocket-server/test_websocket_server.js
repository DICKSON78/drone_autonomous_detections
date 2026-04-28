/**
 * tests/test_websocket_server.js
 * Basic unit tests for client_manager and message_handler.
 * Run: node tests/test_websocket_server.js
 */

const assert = require("assert");
const { ClientManager } = require("../client_manager");
const { formatKafkaMessage, handleClientMessage } = require("../message_handler");

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ ${name}\n    ${err.message}`);
    failed++;
  }
}

// ── ClientManager ─────────────────────────────────────────────────────────────

console.log("\nClientManager");

test("add() assigns a unique ID and returns it", () => {
  const cm = new ClientManager();
  const ws  = { readyState: 1, send: () => {} };
  const req = { headers: {}, socket: { remoteAddress: "1.2.3.4" } };
  const id  = cm.add(ws, req);
  assert.ok(typeof id === "string" && id.length === 8);
  assert.strictEqual(cm.size, 1);
});

test("remove() decrements size", () => {
  const cm  = new ClientManager();
  const ws  = { readyState: 1, send: () => {} };
  const req = { headers: {}, socket: { remoteAddress: "1.2.3.4" } };
  const id  = cm.add(ws, req);
  cm.remove(id);
  assert.strictEqual(cm.size, 0);
});

test("broadcast() respects per-client filter", () => {
  const cm = new ClientManager();
  const makeWS = () => {
    const received = [];
    return { readyState: 1, send: (d) => received.push(JSON.parse(d)), received };
  };
  const req = { headers: {}, socket: { remoteAddress: "1.2.3.4" } };

  const ws1 = makeWS();
  const ws2 = makeWS();
  const id1 = cm.add(ws1, req);
  const id2 = cm.add(ws2, req);

  cm.setFilter(id1, ["telemetry"]);
  cm.setFilter(id2, ["detection"]);

  cm.broadcast({ type: "telemetry", data: {} });
  assert.strictEqual(ws1.received.length, 1, "ws1 should receive telemetry");
  assert.strictEqual(ws2.received.length, 0, "ws2 should not receive telemetry");
});

test("broadcast() sends to all when filter is empty", () => {
  const cm  = new ClientManager();
  const received = [];
  const ws  = { readyState: 1, send: (d) => received.push(d) };
  const req = { headers: {}, socket: { remoteAddress: "1.2.3.4" } };
  cm.add(ws, req);  // no filter set = receive all
  cm.broadcast({ type: "anything", data: {} });
  assert.strictEqual(received.length, 1);
});

// ── MessageHandler ────────────────────────────────────────────────────────────

console.log("\nMessageHandler");

test("formatKafkaMessage maps topic to type", () => {
  const msg = formatKafkaMessage("drone.telemetry", { bat: 80 });
  assert.strictEqual(msg.type, "telemetry");
  assert.strictEqual(msg.topic, "drone.telemetry");
  assert.deepStrictEqual(msg.data, { bat: 80 });
  assert.ok(typeof msg.timestamp === "number");
});

test("formatKafkaMessage uses 'unknown' for unmapped topics", () => {
  const msg = formatKafkaMessage("some.random.topic", {});
  assert.strictEqual(msg.type, "unknown");
});

test("handleClientMessage handles subscribe", () => {
  const cm  = new ClientManager();
  const ws  = { readyState: 1, send: () => {} };
  const req = { headers: {}, socket: { remoteAddress: "1.2.3.4" } };
  const id  = cm.add(ws, req);
  const raw = JSON.stringify({ type: "subscribe", data: { types: ["telemetry", "detection"] } });
  const { reply } = handleClientMessage(raw, id, cm);
  assert.strictEqual(reply.type, "subscribed");
  assert.deepStrictEqual(reply.filter, ["telemetry", "detection"]);
});

test("handleClientMessage handles ping → pong", () => {
  const cm  = new ClientManager();
  const ws  = { readyState: 1, send: () => {} };
  const req = { headers: {}, socket: { remoteAddress: "1.2.3.4" } };
  const id  = cm.add(ws, req);
  const ts  = 1234567890;
  const raw = JSON.stringify({ type: "ping", timestamp: ts });
  const { reply } = handleClientMessage(raw, id, cm);
  assert.strictEqual(reply.type, "pong");
  assert.strictEqual(reply.timestamp, ts);
});

test("handleClientMessage returns error on bad JSON", () => {
  const cm  = new ClientManager();
  const ws  = { readyState: 1, send: () => {} };
  const req = { headers: {}, socket: { remoteAddress: "1.2.3.4" } };
  const id  = cm.add(ws, req);
  const { reply } = handleClientMessage("not json {{", id, cm);
  assert.strictEqual(reply.type, "error");
});

// ── Summary ───────────────────────────────────────────────────────────────────

console.log(`\n${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);