/**
 * api.js — HTTP client for the Feedback Service REST API.
 */

const BASE = `http://${window.location.hostname}:8005`;

async function _post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

async function _get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

export const FeedbackAPI = {
  health:       ()               => _get("/health"),
  stats:        ()               => _get("/stats"),
  voices:       ()               => _get("/voices"),
  audioDevices: ()               => _get("/audio-devices"),
  speak:        (message, priority = "normal") => _post("/speak",    { message, priority }),
  announce:     (event, details = "")          => _post("/announce", { event, details }),
};