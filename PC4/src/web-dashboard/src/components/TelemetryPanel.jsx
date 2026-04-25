import React from "react";
import { round, batteryLabel, formatTime } from "../utils/formatters";
import "./TelemetryPanel.css";

export default function TelemetryPanel({ telemetry }) {
  if (!telemetry) {
    return <div className="telemetry-panel telemetry-panel--empty">No telemetry data yet…</div>;
  }

  const { latitude, longitude, altitude, battery, speed, heading, _ts } = telemetry;

  const rows = [
    ["📍 Latitude",  round(latitude,  6)],
    ["📍 Longitude", round(longitude, 6)],
    ["🏔 Altitude",  altitude != null ? `${round(altitude, 1)} m` : "–"],
    ["🔋 Battery",   batteryLabel(battery)],
    ["💨 Speed",     speed != null ? `${round(speed, 1)} m/s` : "–"],
    ["🧭 Heading",   heading != null ? `${round(heading, 0)}°` : "–"],
    ["🕐 Updated",   formatTime(_ts)],
  ];

  return (
    <div className="telemetry-panel">
      <h3 className="panel-title">Telemetry</h3>
      <table className="telemetry-table">
        <tbody>
          {rows.map(([label, val]) => (
            <tr key={label}>
              <td className="telemetry-label">{label}</td>
              <td className="telemetry-value">{val}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}