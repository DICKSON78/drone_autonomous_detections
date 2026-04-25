import React from "react";
import "./StatusCard.css";

export default function StatusCard({ icon, label, value, status }) {
  return (
    <div className={`status-card ${status ? `status-card--${status}` : ""}`}>
      <div className="status-card__icon">{icon}</div>
      <div className="status-card__body">
        <div className="status-card__label">{label}</div>
        <div className="status-card__value">{value ?? "–"}</div>
      </div>
    </div>
  );
}
