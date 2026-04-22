import React from 'react';
import PropTypes from 'prop-types';
import '../styles/components.css';

/**
 * DetectionList - Displays detailed list of object detections
 */
function DetectionList({ detections }) {
  return (
    <div className="detection-list-container">
      {detections.map((detection, idx) => {
        const detectionData = detection.data?.detections || [];

        return (
          <div key={idx} className="detection-group">
            <div className="detection-group-header">
              <span className="count">{detectionData.length} objects</span>
              <span className="timestamp">
                {new Date(detection.timestamp).toLocaleTimeString()}
              </span>
            </div>

            <div className="detections-grid">
              {detectionData.map((obj, objIdx) => (
                <div key={objIdx} className="detection-card">
                  <div className="detection-header">
                    <span className="class-name">{obj.class_name}</span>
                    <span className="confidence">
                      {(obj.confidence * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="detection-details">
                    <div className="detail">
                      <span className="label">Bounding Box:</span>
                      <span className="value">
                        [{obj.bbox?.[0]?.toFixed(0)}, {obj.bbox?.[1]?.toFixed(0)},
                        {obj.bbox?.[2]?.toFixed(0)}, {obj.bbox?.[3]?.toFixed(0)}]
                      </span>
                    </div>

                    <div className="confidence-bar">
                      <div
                        className="confidence-fill"
                        style={{
                          width: `${obj.confidence * 100}%`,
                          backgroundColor: obj.confidence > 0.7
                            ? '#4caf50'
                            : obj.confidence > 0.5
                              ? '#ff9800'
                              : '#f44336',
                        }}
                      />
                    </div>

                    {obj.attributes && (
                      <div className="attributes">
                        {Object.entries(obj.attributes).map(([key, val]) => (
                          <span key={key} className="attribute">
                            {key}: {val}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

DetectionList.propTypes = {
  detections: PropTypes.array.isRequired,
};

export default DetectionList;
