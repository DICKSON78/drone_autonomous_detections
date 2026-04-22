import React from 'react';
import PropTypes from 'prop-types';
import '../styles/components.css';

/**
 * TelemetryPanel - Displays drone telemetry data
 */
function TelemetryPanel({ telemetry }) {
  if (!telemetry) {
    return (
      <div className="telemetry-panel empty">
        <h3>📡 Telemetry</h3>
        <p>Waiting for telemetry data...</p>
      </div>
    );
  }

  const data = telemetry.data || {};
  const gps = data.gps || {};
  const battery = data.battery || {};
  const imu = data.imu || {};

  return (
    <div className="telemetry-panel">
      <h3>📡 Live Telemetry</h3>
      <div className="telemetry-grid">
        <div className="telemetry-group">
          <h4>📍 GPS Position</h4>
          <div className="telemetry-item">
            <span className="label">Latitude:</span>
            <span className="value">{gps.latitude?.toFixed(6) || 'N/A'}</span>
          </div>
          <div className="telemetry-item">
            <span className="label">Longitude:</span>
            <span className="value">{gps.longitude?.toFixed(6) || 'N/A'}</span>
          </div>
          <div className="telemetry-item">
            <span className="label">Altitude:</span>
            <span className="value">{gps.altitude?.toFixed(2) || 'N/A'} m</span>
          </div>
        </div>

        <div className="telemetry-group">
          <h4>🔋 Battery</h4>
          <div className="battery-display">
            <div className="battery-bar">
              <div
                className="battery-level"
                style={{
                  width: `${(battery.percentage || 0) * 100}%`,
                  backgroundColor: battery.percentage > 0.3 ? '#4caf50' : '#f44336',
                }}
              />
            </div>
            <span className="battery-percentage">{(battery.percentage * 100).toFixed(1)}%</span>
          </div>
          <div className="telemetry-item">
            <span className="label">Voltage:</span>
            <span className="value">{battery.voltage?.toFixed(2) || 'N/A'} V</span>
          </div>
          <div className="telemetry-item">
            <span className="label">Current:</span>
            <span className="value">{battery.current?.toFixed(2) || 'N/A'} A</span>
          </div>
        </div>

        <div className="telemetry-group">
          <h4>📊 IMU</h4>
          <div className="telemetry-item">
            <span className="label">Roll:</span>
            <span className="value">{imu.roll?.toFixed(2) || 'N/A'}°</span>
          </div>
          <div className="telemetry-item">
            <span className="label">Pitch:</span>
            <span className="value">{imu.pitch?.toFixed(2) || 'N/A'}°</span>
          </div>
          <div className="telemetry-item">
            <span className="label">Yaw:</span>
            <span className="value">{imu.yaw?.toFixed(2) || 'N/A'}°</span>
          </div>
        </div>
      </div>

      <div className="telemetry-timestamp">
        Last updated: {new Date(telemetry.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}

TelemetryPanel.propTypes = {
  telemetry: PropTypes.object,
};

export default TelemetryPanel;
