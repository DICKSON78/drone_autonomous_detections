import React from 'react';
import PropTypes from 'prop-types';
import '../styles/pages.css';
import AlertFeed from '../components/AlertFeed';

/**
 * Feedback page - Text-to-speech feedback messages and announcements
 */
function Feedback({ feedbackMessages }) {
  const priorityColors = {
    emergency: '#f44336',
    high: '#ff9800',
    normal: '#2196f3',
    low: '#4caf50',
  };

  const getPriorityLabel = (priority) => {
    const labels = {
      emergency: '🚨 EMERGENCY',
      high: '⚠️ WARNING',
      normal: 'ℹ️ INFO',
      low: '✓ LOW',
    };
    return labels[priority] || priority;
  };

  return (
    <div className="page feedback-page">
      <div className="page-header">
        <h2>🔊 Feedback & Announcements</h2>
        <p>Text-to-speech messages and system announcements</p>
      </div>

      {feedbackMessages.length > 0 ? (
        <div className="feedback-messages">
          {feedbackMessages.map((msg, idx) => {
            const priority = msg.data?.priority || 'normal';
            const message = msg.data?.message || '';

            return (
              <div
                key={idx}
                className="feedback-message"
                style={{ borderLeftColor: priorityColors[priority] }}
              >
                <div className="feedback-priority">
                  {getPriorityLabel(priority)}
                </div>
                <div className="feedback-content">
                  <p className="message">{message}</p>
                  <div className="feedback-meta">
                    <span className="trigger">
                      Trigger: {msg.data?.trigger || 'unknown'}
                    </span>
                    <span className="time">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="no-data">
          <p>No feedback messages yet</p>
        </div>
      )}

      <div className="feedback-stats">
        <div className="stat">
          <span className="label">Total Messages:</span>
          <span className="value">{feedbackMessages.length}</span>
        </div>
        <div className="stat">
          <span className="label">Emergency:</span>
          <span className="value">
            {feedbackMessages.filter(m => m.data?.priority === 'emergency').length}
          </span>
        </div>
        <div className="stat">
          <span className="label">Warnings:</span>
          <span className="value">
            {feedbackMessages.filter(m => m.data?.priority === 'high').length}
          </span>
        </div>
      </div>
    </div>
  );
}

Feedback.propTypes = {
  feedbackMessages: PropTypes.array.isRequired,
};

export default Feedback;
