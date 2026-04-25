import React from "react";
import StatusCard    from "../components/StatusCard";
import TelemetryPanel from "../components/TelemetryPanel";
import AlertFeed     from "../components/AlertFeed";
import DetectionList from "../components/DetectionList";
import { batteryLabel, round } from "../utils/formatters";
import "./Dashboard.css";

export default function Dashboard({ connected, telemetry, detections, feedbackHistory, messageCount }) {
  const battery = telemetry?.battery;
  const battStatus = battery == null ? null : battery > 50 ? "ok" : battery > 20 ? "warn" : "error";

  return (
    <div className="dashboard">
      <section className="dashboard-cards">
        <StatusCard icon="📡" label="Connection"  value={connected ? "Live"  : "Offline"}  status={connected ? "ok" : "error"} />
        <StatusCard icon="💬" label="Messages"    value={messageCount} />
        <StatusCard icon="🔋" label="Battery"     value={batteryLabel(battery)} status={battStatus} />
        <StatusCard icon="🏔" label="Altitude"    value={telemetry?.altitude != null ? `${round(telemetry.altitude, 1)} m` : "–"} />
        <StatusCard icon="👁" label="Detections"  value={detections.length} />
        <StatusCard icon="🔊" label="Voice msgs"  value={feedbackHistory.length} />
      </section>

      <div className="dashboard-grid">
        <section className="dashboard-panel">
          <h2 className="panel-title">Telemetry</h2>
          <TelemetryPanel telemetry={telemetry} />
        </section>

        <section className="dashboard-panel">
          <h2 className="panel-title">Recent Detections</h2>
          <DetectionList detections={detections.slice(0, 5)} />
        </section>

        <section className="dashboard-panel dashboard-panel--wide">
          <h2 className="panel-title">Voice Feedback Log</h2>
          <AlertFeed items={feedbackHistory.slice(0, 15)} />
        </section>
      </div>
    </div>
  );
}