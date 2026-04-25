import React, { useState } from "react";
import AlertFeed from "../components/AlertFeed";
import { FeedbackAPI } from "../services/api";
import "./FeedbackPage.css";

const PRIORITIES = ["low", "normal", "high", "emergency"];

export default function FeedbackPage({ history = [] }) {
  const [filter,   setFilter]   = useState("");
  const [message,  setMessage]  = useState("");
  const [priority, setPriority] = useState("normal");
  const [sending,  setSending]  = useState(false);
  const [status,   setStatus]   = useState(null);

  const filtered = filter
    ? history.filter((h) => (h.priority ?? "") === filter)
    : history;

  const counts = PRIORITIES.reduce((acc, p) => {
    acc[p] = history.filter((h) => h.priority === p).length;
    return acc;
  }, {});

  const handleSpeak = async () => {
    if (!message.trim()) return;
    setSending(true);
    setStatus(null);
    try {
      await FeedbackAPI.speak(message.trim(), priority);
      setStatus({ ok: true, text: "Sent!" });
      setMessage("");
    } catch (err) {
      setStatus({ ok: false, text: `Error: ${err.message}` });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="feedback-page">
      <h2 className="panel-title">Voice Feedback</h2>

      {/* Manual speak panel */}
      <div className="speak-panel">
        <h3 className="speak-panel__title">Send Voice Message</h3>
        <div className="speak-row">
          <input
            className="speak-input"
            type="text"
            placeholder="Type a message to speak…"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSpeak()}
          />
          <select className="priority-select" value={priority} onChange={(e) => setPriority(e.target.value)}>
            {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <button className="speak-btn" onClick={handleSpeak} disabled={sending || !message.trim()}>
            {sending ? "…" : "🔊 Speak"}
          </button>
        </div>
        {status && <div className={`speak-status ${status.ok ? "speak-status--ok" : "speak-status--err"}`}>{status.text}</div>}
      </div>

      {/* Stats */}
      <div className="feedback-stats">
        <div className="stat-item"><span className="stat-val">{history.length}</span><span className="stat-label">Total</span></div>
        {PRIORITIES.map((p) => (
          <div key={p} className={`stat-item stat-item--${p}`}>
            <span className="stat-val">{counts[p]}</span>
            <span className="stat-label">{p}</span>
          </div>
        ))}
      </div>

      {/* Filter + history */}
      <div className="feedback-filter">
        <button className={`filter-btn ${!filter ? "filter-btn--active" : ""}`} onClick={() => setFilter("")}>All</button>
        {PRIORITIES.map((p) => (
          <button key={p} className={`filter-btn filter-btn--${p} ${filter === p ? "filter-btn--active" : ""}`} onClick={() => setFilter(filter === p ? "" : p)}>{p}</button>
        ))}
      </div>

      <AlertFeed items={filtered} />
    </div>
  );
}