import React from 'react';
import PropTypes from 'prop-types';
import '../styles/components.css';

/**
 * AlertFeed - Displays a feed of alerts and messages
 */
function AlertFeed({ alerts, maxItems = 10 }) {
  const displayAlerts = alerts.slice(0, maxItems);

  const getSeverityColor = (severity) => {
    const colors = {
      critical: '#f44336',
      warning: '#ff9800',
      info: '#2196f3',
      success: '#4caf50',
    };
    return colors[severity] || '#2196f3';
  };

  return (
    <div className="alert-feed">
      {displayAlerts.length > 0 ? (
        <div className="alerts-list">
          {displayAlerts.map((alert, idx) => (
            <div
              key={idx}
              className="alert-item"
              style={{ borderLeftColor: getSeverityColor(alert.severity) }}
            >
              <div className="alert-time">
                {new Date(alert.timestamp).toLocaleTimeString()}
              </div>
              <div className="alert-content">
                <span className="alert-severity">{alert.severity.toUpperCase()}</span>
                <span className="alert-message">{alert.message}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-message">No alerts</p>
      )}
    </div>
  );
}

AlertFeed.propTypes = {
  alerts: PropTypes.array,
  maxItems: PropTypes.number,
};

AlertFeed.defaultProps = {
  alerts: [],
  maxItems: 10,
};

export default AlertFeed;
