import React from "react";
import { formatTime, priorityClass } from "../utils/formatters";
import "./AlertFeed.css";

export default function AlertFeed({ items = [], maxItems = 20 }) {
  const visible = items.slice(0, maxItems);

  if (!visible.length) {
    return <div className="alert-feed alert-feed--empty">No events yet…</div>;
  }

  return (
    <div className="alert-feed">
      {visible.map((item, i) => (
        <div key={i} className={`alert-item ${priorityClass(item.priority)}`}>
          <span className="alert-time">{formatTime(item._ts)}</span>
          <span className="alert-msg">{item.message ?? item.action ?? JSON.stringify(item)}</span>
          {item.priority && (
            <span className="alert-badge">{item.priority}</span>
          )}
        </div>
      ))}
    </div>
  );
}
