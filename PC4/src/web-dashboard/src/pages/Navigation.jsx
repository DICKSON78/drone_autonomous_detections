import React from 'react';
import PropTypes from 'prop-types';
import '../styles/pages.css';

/**
 * Navigation page - Drone navigation and path planning information
 */
function Navigation({ messages }) {
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#4caf50';
    if (confidence >= 0.5) return '#ff9800';
    return '#f44336';
  };

  return (
    <div className="page navigation-page">
      <div className="page-header">
        <h2>🧭 Navigation & Path Planning</h2>
        <p>Real-time drone navigation decisions and confidence levels</p>
      </div>

      {messages.length > 0 ? (
        <div className="navigation-list">
          {messages.map((msg, idx) => {
            const result = msg.data?.result || {};
            const action = result.next_action || 'N/A';
            const confidence = result.confidence || 0;
            const waypoints = result.waypoints || [];

            return (
              <div key={idx} className="navigation-item">
                <div className="nav-header">
                  <h4>Action: {action}</h4>
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill"
                      style={{
                        width: `${confidence * 100}%`,
                        backgroundColor: getConfidenceColor(confidence),
                      }}
                    />
                    <span className="confidence-text">
                      {(confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {waypoints.length > 0 && (
                  <div className="waypoints">
                    <h5>Waypoints ({waypoints.length}):</h5>
                    <div className="waypoints-grid">
                      {waypoints.map((wp, wpIdx) => (
                        <div key={wpIdx} className="waypoint">
                          <span className="label">WP{wpIdx + 1}</span>
                          <span className="coords">
                            {wp.lat?.toFixed(4)}, {wp.lng?.toFixed(4)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="timestamp">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="no-data">
          <p>No navigation data available</p>
        </div>
      )}
    </div>
  );
}

Navigation.propTypes = {
  messages: PropTypes.array.isRequired,
};

export default Navigation;
