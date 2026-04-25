import React, { useState } from "react";
import DetectionList from "../components/DetectionList";
import "./Detections.css";

export default function Detections({ detections = [] }) {
  const [filter, setFilter] = useState("");

  return (
    <div className="detections-page">
      <div className="detections-header">
        <h2 className="panel-title">Object Detections</h2>
        <input
          className="filter-input"
          type="text"
          placeholder="Filter by class name…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <span className="detections-count">{detections.length} events</span>
      </div>
      <DetectionList detections={detections} filter={filter} />
    </div>
  );
}