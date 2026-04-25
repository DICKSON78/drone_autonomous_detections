/** Format a Unix-ms timestamp to HH:MM:SS */
export function formatTime(ts) {
  if (!ts) return "--:--:--";
  return new Date(ts).toLocaleTimeString();
}

/** Format confidence (0–1) as a percentage string */
export function pct(value) {
  if (value == null) return "–";
  return `${Math.round(value * 100)}%`;
}

/** Return a CSS class name for confidence level */
export function confidenceClass(value) {
  if (value >= 0.85) return "conf-high";
  if (value >= 0.65) return "conf-medium";
  return "conf-low";
}

/** Return a CSS class for priority */
export function priorityClass(priority) {
  const map = {
    emergency: "priority-emergency",
    high:      "priority-high",
    normal:    "priority-normal",
    low:       "priority-low",
  };
  return map[priority] ?? "priority-normal";
}

/** Round a number to N decimal places */
export function round(n, places = 2) {
  if (n == null) return "–";
  return Number(n).toFixed(places);
}

/** Format battery percentage with colour cue */
export function batteryLabel(pct) {
  if (pct == null) return "–";
  const icon = pct > 50 ? "🔋" : pct > 20 ? "🪫" : "⚠️";
  return `${icon} ${Math.round(pct)}%`;
}