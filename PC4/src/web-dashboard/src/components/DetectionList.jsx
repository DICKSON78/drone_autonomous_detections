import React from "react";
import { pct, confidenceClass, formatTime } from "../utils/formatters";
import "./DetectionList.css";

export default function DetectionList({ detections = [], filter = "" }) {
  const items = filter
    ? detections.filter((d) => {
        const name = (d.class_name ?? d.detections?.[0]?.class_name ?? "").toLowerCase();
        return name.includes(filter.toLowerCase());
      })
    : detections;

  if (!items.length) {
    return <div className="detection-list--empty">No detections{filter ? ` matching "${filter}"` : " yet"}…</div>;
  }

  return (
    <div className="detection-list">
      {items.map((event, i) => {
        const dets = event.detections ?? [event];
        return (
          <div key={i} className="detection-card">
            <div className="detection-card__header">
              <span className="detection-time">{formatTime(event._ts)}</span>
              <span className="detection-count">{dets.length} object{dets.length !== 1 ? "s" : ""}</span>
            </div>
            {dets.map((d, j) => (
              <div key={j} className="detection-row">
                <span className="detection-class">{d.class_name ?? "unknown"}</span>
                <div className="detection-bar-wrap">
                  <div
                    className={`detection-bar ${confidenceClass(d.confidence)}`}
                    style={{ width: pct(d.confidence) }}
                  />
                </div>
                <span className="detection-pct">{pct(d.confidence)}</span>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
