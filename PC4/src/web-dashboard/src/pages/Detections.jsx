import React, { useState } from 'react';
import PropTypes from 'prop-types';
import '../styles/pages.css';
import DetectionList from '../components/DetectionList';

/**
 * Detections page - Detailed list of all detected objects
 */
function Detections({ detections }) {
  const [filterClass, setFilterClass] = useState('all');

  // Extract unique classes from detections
  const classes = ['all', ...new Set(
    detections.flatMap(d => d.data?.detections?.map(det => det.class_name) || [])
  )];

  // Filter detections
  const filteredDetections = filterClass === 'all'
    ? detections
    : detections.filter(d =>
        d.data?.detections?.some(det => det.class_name === filterClass)
      );

  return (
    <div className="page detections-page">
      <div className="page-header">
        <h2>🎯 Object Detections</h2>
        <p>Real-time detected objects from drone camera feed</p>
      </div>

      <div className="filter-bar">
        <label>Filter by class:</label>
        <select value={filterClass} onChange={(e) => setFilterClass(e.target.value)}>
          {classes.map(cls => (
            <option key={cls} value={cls}>
              {cls === 'all' ? 'All Classes' : cls}
            </option>
          ))}
        </select>
        <span className="count">{filteredDetections.length} results</span>
      </div>

      {filteredDetections.length > 0 ? (
        <DetectionList detections={filteredDetections} />
      ) : (
        <div className="no-data">
          <p>No detections found</p>
        </div>
      )}
    </div>
  );
}

Detections.propTypes = {
  detections: PropTypes.array.isRequired,
};

export default Detections;
