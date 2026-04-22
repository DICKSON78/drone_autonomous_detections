import React from 'react';
import PropTypes from 'prop-types';
import '../styles/pages.css';
import StatusCard from '../components/StatusCard';
import TelemetryPanel from '../components/TelemetryPanel';
import AlertFeed from '../components/AlertFeed';

/**
 * Dashboard page - Main overview of drone system status
 */
function Dashboard({ stats, isConnected }) {
  const latestTelemetry = stats.telemetry;
  const recentDetections = stats.detections.slice(0, 5);
  const recentFeedback = stats.feedback.slice(0, 5);

  return (
    <div className="page dashboard-page">
      <section className="dashboard-grid">
        {/* Top Row: Status Cards */}
        <div className="cards-row">
          <StatusCard
            title="Connection Status"
            value={isConnected ? 'Connected' : 'Disconnected'}
            status={isConnected ? 'active' : 'inactive'}
            icon="🔗"
          />
          <StatusCard
            title="Total Messages"
            value={stats.totalMessages}
            status="info"
            icon="📨"
          />
          <StatusCard
            title="Recent Detections"
            value={stats.detections.length}
            status={stats.detections.length > 0 ? 'alert' : 'normal'}
            icon="🎯"
          />
          <StatusCard
            title="Telemetry Status"
            value={latestTelemetry ? 'Active' : 'Waiting'}
            status={latestTelemetry ? 'active' : 'inactive'}
            icon="📊"
          />
        </div>

        {/* Middle Row: Telemetry */}
        <div className="telemetry-row">
          <TelemetryPanel telemetry={latestTelemetry} />
        </div>

        {/* Bottom Row: Alerts and Feedback */}
        <div className="alerts-row">
          <div className="alert-section">
            <h3>🚨 Recent Detections</h3>
            {recentDetections.length > 0 ? (
              <div className="detection-list">
                {recentDetections.map((det, idx) => (
                  <div key={idx} className="detection-item">
                    <span className="time">
                      {new Date(det.timestamp).toLocaleTimeString()}
                    </span>
                    <span className="count">
                      {det.data?.detections?.length || 0} objects detected
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty">No recent detections</p>
            )}
          </div>

          <div className="feedback-section">
            <h3>🔊 Recent Feedback</h3>
            {recentFeedback.length > 0 ? (
              <div className="feedback-list">
                {recentFeedback.map((fb, idx) => (
                  <div key={idx} className="feedback-item">
                    <span className="priority">[{fb.data?.priority?.toUpperCase()}]</span>
                    <span className="message">{fb.data?.message}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty">No recent feedback</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

Dashboard.propTypes = {
  stats: PropTypes.shape({
    totalMessages: PropTypes.number,
    telemetry: PropTypes.object,
    detections: PropTypes.array,
    feedback: PropTypes.array,
  }).isRequired,
  isConnected: PropTypes.bool.isRequired,
};

export default Dashboard;
