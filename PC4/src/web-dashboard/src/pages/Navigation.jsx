import React from "react";
import { pct, confidenceClass, formatTime } from "../utils/formatters";
import "./Navigation.css";

export default function Navigation({ events = [] }) {
  const latest = events[0] ?? null;

  return (
    <div className="navigation-page">
      <h2 className="panel-title">Navigation &amp; Planning</h2>

      {latest ? (
        <div className="nav-current">
          <div className="nav-current__label">Current Action</div>
          <div className="nav-current__action">{latest.action ?? "–"}</div>
          <div className={`nav-confidence ${confidenceClass(latest.confidence)}`}>
            Confidence: {pct(latest.confidence)}
          </div>
          {latest.waypoint && (
            <div className="nav-waypoint">
              Waypoint: {JSON.stringify(latest.waypoint)}
            </div>
          )}
        </div>
      ) : (
        <div className="nav-empty">No navigation data yet…</div>
      )}

      <h3 className="panel-title" style={{ marginTop: 20 }}>Navigation History</h3>
      <div className="nav-history">
        {events.length === 0 && <div className="nav-empty">No events yet.</div>}
        {events.map((ev, i) => (
          <div key={i} className="nav-row">
            <span className="nav-time">{formatTime(ev._ts)}</span>
            <span className="nav-action">{ev.action ?? "–"}</span>
            <div className="nav-bar-wrap">
              <div className={`nav-bar ${confidenceClass(ev.confidence)}`} style={{ width: pct(ev.confidence) }} />
            </div>
            <span className="nav-pct">{pct(ev.confidence)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}